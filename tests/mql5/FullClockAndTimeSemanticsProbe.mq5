#property strict
#property script_show_inputs
// Observe only. No DLLs, orders, custom ticks, symbols or terminal settings.
input string RunId="LOCAL_RUN_ID";
string symbols[]={"US30Cash","EURUSD","USDCHF"};
void OnStart(){
 if(!CaptureSessionSnapshot())return;
 string file=RunId+"_native.csv";
 if(FileIsExist(file)||FileIsExist(RunId+"_markers.txt")){Print("CLOCK_ATTESTATION|REFUSE_OVERWRITE");return;}
 int f=FileOpen(file,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',',CP_UTF8);
 if(f==INVALID_HANDLE){Print("CLOCK_ATTESTATION|FILE_ERROR");return;}
 int markers=FileOpen(RunId+"_markers.txt",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ,0,CP_UTF8);
 if(markers==INVALID_HANDLE){FileClose(f);Print("CLOCK_ATTESTATION|MARKER_FILE_ERROR");return;}
 string begin=StringFormat("CLOCK_ATTESTATION_BEGIN|run=%s|capture_gmt_label=%I64d|monotonic_ms=%I64u",RunId,(long)TimeGMT(),GetTickCount64());
 Print(begin);FileWriteString(markers,begin+"\r\n");FileFlush(markers);
 FileWrite(f,"frame","symbol","tester","connected","terminal_build","mono_start_ms","gmt_before","gmt_before_mono_ms","time_local","local_mono_ms","time_gmt","gmt_mono_ms","time_current","current_mono_ms","time_trade_server","server_mono_ms","tick_ok","bid","ask","tick_time","tick_time_msc","tick_mono_ms","gmt_offset","dst","mono_end_ms");
 FileFlush(f);
 for(int i=0;i<50;i++){
  for(int s=0;s<ArraySize(symbols);s++){
   ulong start=GetTickCount64();datetime before=TimeGMT();ulong b=GetTickCount64();
   datetime local=TimeLocal();ulong l=GetTickCount64();
   datetime gmt=TimeGMT();ulong g=GetTickCount64();
   datetime current=TimeCurrent();ulong c=GetTickCount64();
   datetime server=TimeTradeServer();ulong t=GetTickCount64();
   MqlTick q;ZeroMemory(q);bool ok=SymbolInfoTick(symbols[s],q);ulong k=GetTickCount64();
   FileWrite(f,i,symbols[s],MQLInfoInteger(MQL_TESTER),TerminalInfoInteger(TERMINAL_CONNECTED),TerminalInfoInteger(TERMINAL_BUILD),
    start,(long)before,b,(long)local,l,(long)gmt,g,(long)current,c,(long)server,t,
    ok?1:0,DoubleToString(q.bid,10),DoubleToString(q.ask,10),(long)q.time,q.time_msc,k,
    TimeGMTOffset(),TimeDaylightSavings(),GetTickCount64());
  }
  FileFlush(f);if(i<49)Sleep(1000);
 }
 FileClose(f);
 string end=StringFormat("CLOCK_ATTESTATION_END|run=%s|frames=50|records=150|capture_gmt_label=%I64d|monotonic_ms=%I64u|orders_sent=0",RunId,(long)TimeGMT(),GetTickCount64());
 FileWriteString(markers,end+"\r\n");FileFlush(markers);FileClose(markers);Print(end);
}


bool CaptureSessionSnapshot()
  {
   string session_file=RunId+"_sessions.txt";
   if(FileIsExist(session_file)){Print("SESSION_REFUSE_OVERWRITE");return false;}
   int session_handle=FileOpen(session_file,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
   if(session_handle==INVALID_HANDLE){Print("SESSION_FILE_ERROR");return false;}
   const string symbol = "US30Cash";
   string days[7] = {"SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY",
                    "THURSDAY", "FRIDAY", "SATURDAY"};
   long selected = 0;
   bool symbol_exists = SymbolInfoInteger(symbol, SYMBOL_SELECT, selected);
   datetime server_now = TimeTradeServer();
   datetime utc_now = TimeGMT();

   FileWriteString(session_handle,StringFormat("XM_SESSION_PROBE|START|symbol=%s|symbol_selected=%s|server=%s",
               symbol, symbol_exists && selected != 0 ? "YES" : "NO",
               AccountInfoString(ACCOUNT_SERVER))+"\r\n");
   FileWriteString(session_handle,StringFormat("XM_SESSION_PROBE|CLOCK|server_time=%s|utc_time=%s|offset_seconds=%I64d",
               TimeToString(server_now, TIME_DATE|TIME_SECONDS),
               TimeToString(utc_now, TIME_DATE|TIME_SECONDS),
               (long)(server_now - utc_now))+"\r\n");

   for(int day = 0; day < 7; day++)
     {
      for(uint index = 0; index < 16; index++)
        {
         datetime from_time = 0;
         datetime to_time = 0;
         if(!SymbolInfoSessionQuote(symbol, (ENUM_DAY_OF_WEEK)day, index,
                                    from_time, to_time))
            break;
         FileWriteString(session_handle,StringFormat("XM_SESSION_PROBE|QUOTE|day=%s|index=%u|from=%s|to=%s",
                     days[day], index, TimeToString(from_time, TIME_MINUTES),
                     TimeToString(to_time, TIME_MINUTES))+"\r\n");
        }
      for(uint index = 0; index < 16; index++)
        {
         datetime from_time = 0;
         datetime to_time = 0;
         if(!SymbolInfoSessionTrade(symbol, (ENUM_DAY_OF_WEEK)day, index,
                                    from_time, to_time))
            break;
         FileWriteString(session_handle,StringFormat("XM_SESSION_PROBE|TRADE|day=%s|index=%u|from=%s|to=%s",
                     days[day], index, TimeToString(from_time, TIME_MINUTES),
                     TimeToString(to_time, TIME_MINUTES))+"\r\n");
        }
     }

   FileWriteString(session_handle,"XM_SESSION_PROBE|END\r\n");
   FileFlush(session_handle);FileClose(session_handle);return true;
  }
