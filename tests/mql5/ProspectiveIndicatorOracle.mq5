#property strict
#include "HeikinAshiCore.mqh"
const string RUN="__RUN__";
void OnStart(){
 string symbol="LABPIPE_"+StringSubstr(RUN,StringLen(RUN)-8);
 if(!CustomSymbolCreate(symbol,"ResearchDiagnostics"))return;
 CustomSymbolSetInteger(symbol,SYMBOL_DIGITS,2);
 MqlRates bars[],minutes[];ArrayResize(bars,500);ArrayResize(minutes,2500);
 for(int i=0;i<500;i++){
  ZeroMemory(bars[i]);bars[i].time=(datetime)(946857600+i*300);
  bars[i].close=1000+(i%37)*3-(i%11)*2;bars[i].open=bars[i].close+(i%3)-1;
  bars[i].high=MathMax(bars[i].open,bars[i].close)+5+i%7;
  bars[i].low=MathMin(bars[i].open,bars[i].close)-4-i%5;bars[i].tick_volume=5;
  for(int m=0;m<5;m++){minutes[i*5+m]=bars[i];minutes[i*5+m].time+=m*60;minutes[i*5+m].tick_volume=1;}
 }
 if(CustomRatesUpdate(symbol,minutes)!=2500||!SymbolSelect(symbol,true))return;
 int stoch=iStochastic(symbol,PERIOD_M5,5,3,3,MODE_SMA,STO_LOWHIGH),atr=iATR(symbol,PERIOD_M5,14);
 double k[],a[];bool ready=false;
 for(int attempt=0;attempt<500&&!IsStopped();attempt++){
  if(CopyBuffer(stoch,0,1,499,k)==499&&CopyBuffer(atr,0,1,499,a)==499){ready=true;break;}Sleep(10);
 }
 if(!ready)return;
 int f=FileOpen(RUN+"_oracle.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 if(f==INVALID_HANDLE)return;
 FileWrite(f,"index","time","open","high","low","close","volume","main_k","atr","ha_direction","ha_ready");
 HeikinAshiState ha;
 for(int i=0;i<499;i++){
  if(!ha.Append((long)bars[i].time,bars[i].open,bars[i].high,bars[i].low,bars[i].close,((long)bars[i].time+300)*1000-1)){FileClose(f);return;}
  FileWrite(f,i,(long)bars[i].time,DoubleToString(bars[i].open,16),DoubleToString(bars[i].high,16),DoubleToString(bars[i].low,16),DoubleToString(bars[i].close,16),5,DoubleToString(k[i],16),DoubleToString(a[i],16),ha.bars[0].direction,ha.Ready()?1:0);
 }
 FileFlush(f);FileClose(f);IndicatorRelease(stoch);IndicatorRelease(atr);
 Print("PIPELINE_ORACLE_COMPLETE ",RUN);
}
