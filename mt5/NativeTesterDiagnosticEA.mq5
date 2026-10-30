// Observation wrapper only. The frozen strategy source/includes are unchanged.
#define OnInit FrozenOnInit
#define OnTick FrozenOnTick
#define OnDeinit FrozenOnDeinit
#include "StochasticBarDecisionResearchEA.mq5"
#undef OnInit
#undef OnTick
#undef OnDeinit
int diagnostic_main=INVALID_HANDLE;
datetime diagnostic_last=0;

int OnInit()
  {
   int result=FrozenOnInit();if(result!=INIT_SUCCEEDED)return result;
   diagnostic_main=FileOpen(OutputFile+".native_main.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
   if(diagnostic_main==INVALID_HANDLE)return INIT_FAILED;
   FileWrite(diagnostic_main,"bar_open_native","main_k","previous_main_k","signal","feature_cutoff_native_msc");
   return INIT_SUCCEEDED;
  }
void OnTick()
  {
   FrozenOnTick();
   datetime closed=iTime(sym,PERIOD_M5,1);
   if(closed==diagnostic_last || closed<1704153600 || closed>=1704240000)return;
   double observed[];
   if(Buffer(stoch,0,2,observed))
     {FileWrite(diagnostic_main,(long)closed,DoubleToString(observed[0],16),DoubleToString(observed[1],16),ResearchSignal(observed[1],observed[0]),ResearchSignalCutoff((long)closed));diagnostic_last=closed;}
  }
void ExportNativeRates(ENUM_TIMEFRAMES frame,string suffix)
  {
   MqlRates observed[];int count=CopyRates(sym,frame,(datetime)1704153600,(datetime)1704239999,observed);
   int file=FileOpen(OutputFile+suffix,FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
   if(file==INVALID_HANDLE){Print("NATIVE_DIAGNOSTIC_EXPORT_FAILED");return;}
   FileWrite(file,"time","open","high","low","close","tick_volume","spread","real_volume");
   for(int i=0;i<count;i++)FileWrite(file,(long)observed[i].time,DoubleToString(observed[i].open,16),DoubleToString(observed[i].high,16),DoubleToString(observed[i].low,16),DoubleToString(observed[i].close,16),observed[i].tick_volume,observed[i].spread,observed[i].real_volume);
   FileClose(file);PrintFormat("NATIVE_DIAGNOSTIC_RATES|%s|%d",suffix,count);
  }
void OnDeinit(const int reason)
  {
   if(diagnostic_main!=INVALID_HANDLE){FileClose(diagnostic_main);diagnostic_main=INVALID_HANDLE;}
   ExportNativeRates(PERIOD_M1,".native_M1.csv");ExportNativeRates(PERIOD_M5,".native_M5.csv");
   FrozenOnDeinit(reason);
  }
