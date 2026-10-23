#property script_show_inputs
// Observe only. No DLLs, orders, custom ticks, symbols or terminal settings.
input string RunId="attest_20261023_a1";
string symbols[]={"US30Cash","EURUSD","USDCHF"};
void OnStart(){
 string file=RunId+"_native.csv";
 if(FileIsExist(file)){Print("CLOCK_ATTESTATION|REFUSE_OVERWRITE");return;}
 int f=FileOpen(file,FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',',CP_UTF8);
 if(f==INVALID_HANDLE){Print("CLOCK_ATTESTATION|FILE_ERROR");return;}
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
 FileClose(f);PrintFormat("CLOCK_ATTESTATION|END|run=%s|frames=50|orders_sent=0",RunId);
}
