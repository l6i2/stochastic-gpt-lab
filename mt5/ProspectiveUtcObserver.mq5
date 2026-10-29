#property strict
#property version "1.01"
#property description "Read-only native callback observer. No historical queries or trading."
input string CaptureId="pc_a_prospective_utc_v1";
int handle=INVALID_HANDLE;
ulong sequence=0;
string session_id;
string previous="0000000000000000000000000000000000000000000000000000000000000000";

string Digest(const string value)
  {
   uchar data[],key[],result[];
   int count=StringToCharArray(value,data,0,WHOLE_ARRAY,CP_UTF8);
   if(count<1) return "";
   ArrayResize(data,count-1);
   if(CryptEncode(CRYPT_HASH_SHA256,data,key,result)!=32) return "";
   string hex="";
   for(int i=0;i<ArraySize(result);i++) hex+=StringFormat("%02x",result[i]);
   return hex;
  }

void Record(const string kind,const ulong callback_ms,const ulong callback_us,const MqlTick &tick)
  {
   if(handle==INVALID_HANDLE) return;
   ulong read_ms=GetTickCount64();
   datetime receipt=TimeGMT(); // Host-derived, second resolution, NOT attested event UTC.
   string body=StringFormat("{\"kind\":\"%s\",\"capture_id\":\"%s\",\"session_id\":\"%s\",\"sequence\":%I64u,\"symbol\":\"US30Cash\",\"server\":\"XMGlobalSC-MT5 5\",\"callback_uptime_ms\":%I64u,\"callback_program_us\":%I64u,\"read_uptime_ms\":%I64u,\"receipt_host_gmt_seconds\":%I64d,\"connected\":%s,\"time\":%I64d,\"time_msc\":%I64d,\"bid\":%s,\"ask\":%s,\"flags\":%u}",
      kind,CaptureId,session_id,sequence,callback_ms,callback_us,read_ms,(long)receipt,
      TerminalInfoInteger(TERMINAL_CONNECTED)?"true":"false",(long)tick.time,tick.time_msc,
      DoubleToString(tick.bid,16),DoubleToString(tick.ask,16),tick.flags);
   string digest=Digest(previous+"\n"+body);
   if(StringLen(digest)!=64) {FileClose(handle);handle=INVALID_HANDLE;return;}
   // TXT expands lone LF to CRLF. Use explicit CRLF so the ASCII byte count
   // matches the actual write; the hash still covers the unchanged payload.
   string line="{\"previous\":\""+previous+"\",\"sha256\":\""+digest+"\",\"payload\":"+body+"}\r\n";
   uint written=FileWriteString(handle,line);
   if(written!=(uint)StringLen(line))
     {PrintFormat("PROSPECTIVE_OBSERVER|WRITE_FAILED|bytes=%u|expected=%d|error=%d",written,StringLen(line),GetLastError());FileClose(handle);handle=INVALID_HANDLE;return;}
   FileFlush(handle);
   previous=digest;sequence++;
  }

int OnInit()
  {
   string data=TerminalInfoString(TERMINAL_DATA_PATH);
   if(MQLInfoInteger(MQL_TESTER) || _Symbol!="US30Cash" ||
      AccountInfoString(ACCOUNT_SERVER)!="XMGlobalSC-MT5 5" ||
      AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO ||
      StringFind(data,"20C285FE08971A9A2E814AAC44AFC9D2")<0) return INIT_FAILED;
   for(int i=0;i<StringLen(CaptureId);i++)
     {
      ushort c=StringGetCharacter(CaptureId,i);
      if(!((c>='a' && c<='z') || (c>='0' && c<='9') || c=='_')) return INIT_PARAMETERS_INCORRECT;
     }
   if(StringLen(CaptureId)<1 || StringLen(CaptureId)>80) return INIT_PARAMETERS_INCORRECT;
   FolderCreate("ResearchDiagnostics");
   FolderCreate("ResearchDiagnostics\\ProspectiveUTC");
   session_id=StringFormat("%s_%I64u_%I64d_%I64u",CaptureId,GetTickCount64(),ChartID(),GetMicrosecondCount());
   string file="ResearchDiagnostics\\ProspectiveUTC\\"+session_id+".jsonl";
   if(FileIsExist(file)) return INIT_FAILED;
   handle=FileOpen(file,FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ,0,CP_UTF8);
   if(handle==INVALID_HANDLE) return INIT_FAILED;
   MqlTick empty={};Record("SESSION_START",GetTickCount64(),GetMicrosecondCount(),empty);
   if(handle==INVALID_HANDLE) return INIT_FAILED;
   if(!EventSetTimer(5)) return INIT_FAILED;
   return INIT_SUCCEEDED;
  }

void OnTick()
  {
   ulong ms=GetTickCount64(),us=GetMicrosecondCount();
   MqlTick tick={};
   if(SymbolInfoTick(_Symbol,tick)) Record("ONTICK_LATEST_QUOTE",ms,us,tick);
   else Record("QUOTE_READ_FAILED",ms,us,tick);
  }

void OnTimer()
  {
   MqlTick empty={};Record("HEARTBEAT",GetTickCount64(),GetMicrosecondCount(),empty);
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   MqlTick empty={};Record("SESSION_END",GetTickCount64(),GetMicrosecondCount(),empty);
   if(handle!=INVALID_HANDLE) FileClose(handle);
  }
