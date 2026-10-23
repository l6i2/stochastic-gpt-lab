#property script_show_inputs
// Read-only diagnostics: no custom symbols, ticks, orders or clock adjustments.
input string RunId="clock_20261023_a1";
string symbols[]={"US30Cash","EURUSD","USDCHF"};
void OnStart(){
 string file=RunId+"_native.csv";
 if(FileIsExist(file)){Print("CLOCK_PROVENANCE|REFUSE_OVERWRITE");return;}
 int f=FileOpen(file,FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 if(f==INVALID_HANDLE){Print("CLOCK_PROVENANCE|FILE_ERROR");return;}
 FileWrite(f,"sample","symbol","tester","connected","gmt_before","gmt_after","time_current","time_trade_server","time_local","gmt_offset","dst","tick_ok","bid","ask","tick_time","tick_time_msc","history_count","history_last_time_msc","history_error","monotonic_before","monotonic_after");
 for(int i=0;i<8;i++){
  for(int s=0;s<ArraySize(symbols);s++){
   datetime before=TimeGMT();ulong start=GetTickCount64();
   MqlTick q;ZeroMemory(q);bool ok=SymbolInfoTick(symbols[s],q);
   datetime current=TimeCurrent(),server=TimeTradeServer(),local=TimeLocal(),after=TimeGMT();
   ulong end=GetTickCount64();
   // Explicit raw interval around GMT, never used to substitute the rejected quote.
   MqlTick history[];ResetLastError();
   int n=CopyTicksRange(symbols[s],history,COPY_TICKS_ALL,(ulong)(after-3)*1000,(ulong)after*1000);
   int error=GetLastError();long last=n>0?history[n-1].time_msc:0;
   FileWrite(f,i,symbols[s],MQLInfoInteger(MQL_TESTER),TerminalInfoInteger(TERMINAL_CONNECTED),
    (long)before,(long)after,(long)current,(long)server,(long)local,TimeGMTOffset(),TimeDaylightSavings(),
    ok?1:0,DoubleToString(q.bid,10),DoubleToString(q.ask,10),(long)q.time,q.time_msc,n,last,error,start,end);
  }
  FileFlush(f);if(i<7)Sleep(1000);
 }
 FileClose(f);PrintFormat("CLOCK_PROVENANCE|END|run=%s|orders_sent=0",RunId);
}
