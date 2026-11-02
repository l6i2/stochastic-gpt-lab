#property strict
#property description "Isolated metadata and fixed authorized-day history only; no orders."
void OnStart()
  {
   string path=TerminalInfoString(TERMINAL_DATA_PATH);
   StringReplace(path,"/","\\");
   if(StringFind(path,"\\outputs\\pc_a_certification\\native_tester\\terminal")<0) return;
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO || AccountInfoString(ACCOUNT_SERVER)!="XMGlobalSC-MT5 5") return;
   for(int j=0;j<20 && !TerminalInfoInteger(TERMINAL_CONNECTED);j++) Sleep(500);
   SymbolSelect("US30Cash",true);
   string root="__RUN__";
   int meta=FileOpen(root+"_metadata.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
   if(meta==INVALID_HANDLE) return;
   FileWrite(meta,"frame","maxbars","connected","bars","firstdate","server_firstdate","terminal_firstdate","downloaded","error");
   ENUM_TIMEFRAMES frames[2]={PERIOD_M1,PERIOD_M5};
   for(int f=0;f<2;f++)
     {
      ENUM_TIMEFRAMES tf=frames[f];string label=f==0?"M1":"M5";
      MqlRates rates[];int n=-1,err=0;
      for(int attempt=0;attempt<4;attempt++)
        {
         ResetLastError();n=CopyRates("US30Cash",tf,D'2024.01.02 00:00:00',D'2024.01.02 23:59:59',rates);err=GetLastError();
         if(n>0) break;
         Sleep(1000);
        }
      FileWrite(meta,label,TerminalInfoInteger(TERMINAL_MAXBARS),TerminalInfoInteger(TERMINAL_CONNECTED),Bars("US30Cash",tf),SeriesInfoInteger("US30Cash",tf,SERIES_FIRSTDATE),SeriesInfoInteger("US30Cash",tf,SERIES_SERVER_FIRSTDATE),SeriesInfoInteger("US30Cash",tf,SERIES_TERMINAL_FIRSTDATE),n,err);
      if(n>0)
        {
         bool valid=true;for(int i=0;i<n;i++) if(rates[i].time<D'2024.01.02' || rates[i].time>=D'2024.01.03') valid=false;
         if(!valid) continue;
         int file=FileOpen(root+"_"+label+".csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
         if(file==INVALID_HANDLE) continue;
         FileWrite(file,"time","open","high","low","close","tick_volume","spread","real_volume");
         for(int i=0;i<n;i++) FileWrite(file,(long)rates[i].time,DoubleToString(rates[i].open,8),DoubleToString(rates[i].high,8),DoubleToString(rates[i].low,8),DoubleToString(rates[i].close,8),rates[i].tick_volume,rates[i].spread,rates[i].real_volume);
         FileClose(file);
        }
     }
   FileClose(meta);
   TerminalClose(0);
  }
