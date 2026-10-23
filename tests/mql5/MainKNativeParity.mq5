#property strict
// Standalone synthetic/native diagnostic. No account login, orders or research datasets.
__PRODUCTION_FRAGMENT__
#include "ResearchCore.mqh"
const string RUN_ID="__RUN_ID__";
const string CASES[5]={"trend","range","extremes","equality","warmup"};

bool LoadFixture(string name,MqlRates &bars[]){
 int f=FileOpen(RUN_ID+"_"+name+"_input.csv",FILE_READ|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 if(f==INVALID_HANDLE)return false;
 for(int j=0;j<6;j++)FileReadString(f);
 while(!FileIsEnding(f)){
  string index=FileReadString(f);if(index=="")break;
  int i=ArraySize(bars);ArrayResize(bars,i+1);ZeroMemory(bars[i]);
  bars[i].time=(datetime)FileReadNumber(f);bars[i].open=FileReadNumber(f);
  bars[i].high=FileReadNumber(f);bars[i].low=FileReadNumber(f);bars[i].close=FileReadNumber(f);
  bars[i].tick_volume=5;bars[i].spread=1;
 }
 FileClose(f);return ArraySize(bars)>10;
}
int NativeHandle(string symbol){
 MqlParam p[5];for(int i=0;i<5;i++)p[i].type=TYPE_INT;
 p[0].integer_value=5;p[1].integer_value=3;p[2].integer_value=3;
 p[3].integer_value=MODE_SMA;p[4].integer_value=STO_LOWHIGH;
 return IndicatorCreate(symbol,PERIOD_M5,IND_STOCHASTIC,5,p);
}
bool RunFixture(int which,int output){
 MqlRates bars[];if(!LoadFixture(CASES[which],bars))return false;
 string symbol="LABPK_"+StringSubstr(RUN_ID,StringLen(RUN_ID)-8)+"_"+IntegerToString(which);
 if(!CustomSymbolCreate(symbol,"ResearchDiagnostics"))return false;
 if(!CustomSymbolSetInteger(symbol,SYMBOL_DIGITS,8))return false;
 MqlRates minutes[];int total=ArraySize(bars);ArrayResize(minutes,total*5);
 for(int i=0;i<total;i++)for(int m=0;m<5;m++){minutes[i*5+m]=bars[i];minutes[i*5+m].time=bars[i].time+m*60;}
 if(CustomRatesUpdate(symbol,minutes)!=total*5||!SymbolSelect(symbol,true))return false;
 int production=ProductionHandle(symbol),native=NativeHandle(symbol);
 if(production==INVALID_HANDLE||native==INVALID_HANDLE)return false;
 MqlRates actual[];double prod[],nat[],pd[],nd[];int count=total-1;bool ready=false;
 for(int attempt=0;attempt<500&&!IsStopped();attempt++){
  if(CopyRates(symbol,PERIOD_M5,0,total,actual)==total&&Buffer(production,0,count,prod)&&Buffer(production,1,count,pd)
   &&CopyBuffer(native,0,1,count,nat)==count&&CopyBuffer(native,1,1,count,nd)==count){ready=true;break;}
  Sleep(10);
 }
 if(!ready)return false;
 for(int i=0;i<total;i++)if(actual[i].time!=bars[i].time||MathAbs(actual[i].open-bars[i].open)>1e-10
  ||MathAbs(actual[i].high-bars[i].high)>1e-10||MathAbs(actual[i].low-bars[i].low)>1e-10||MathAbs(actual[i].close-bars[i].close)>1e-10)return false;
 bool passed=true;
 for(int i=0;i<count;i++){
  int j=count-1-i;
  int ps=i>=7?ResearchSignal(prod[j+1],prod[j]):0;
  int ns=i>=7?ResearchSignal(nat[i-1],nat[i]):0;
  FileWrite(output,CASES[which],i,(long)bars[i].time,DoubleToString(prod[j],16),DoubleToString(nat[i],16),
   DoubleToString(pd[j],16),DoubleToString(nd[i],16),ps,ns,i>=6?"READY":"WARMUP");
  if(MathAbs(prod[j]-nat[i])>1e-10||MathAbs(pd[j]-nd[i])>1e-10||ps!=ns)passed=false;
 }
 // Change only the excluded last bar; every closed-bar production value must stay unchanged.
 for(int m=0;m<5;m++){minutes[(total-1)*5+m].high+=500;minutes[(total-1)*5+m].low-=500;minutes[(total-1)*5+m].close+=200;}
 if(CustomRatesUpdate(symbol,minutes)!=total*5)return false;
 Sleep(50);double changed[];
 if(!Buffer(production,0,count,changed))return false;
 for(int j=0;j<count;j++)if(MathAbs(changed[j]-prod[j])>1e-10)passed=false;
 IndicatorRelease(production);IndicatorRelease(native);
 PrintFormat("MAIN_K_PARITY|CASE|run=%s|case=%s|rows=%d|passed=%s",RUN_ID,CASES[which],count,passed?"YES":"NO");
 return passed;
}
void OnStart(){
 if(FileIsExist(RUN_ID+"_native.csv")){Print("MAIN_K_PARITY|REFUSE_OVERWRITE");return;}
 PrintFormat("MAIN_K_PARITY|START|run=%s|build=%d|tester=%d",RUN_ID,TerminalInfoInteger(TERMINAL_BUILD),MQLInfoInteger(MQL_TESTER));
 PrintFormat("MAIN_K_PARITY|CLOCK|current=%I64d|server=%I64d|local=%I64d|gmt=%I64d|gmt_offset=%d|dst=%d",
  (long)TimeCurrent(),(long)TimeTradeServer(),(long)TimeLocal(),(long)TimeGMT(),TimeGMTOffset(),TimeDaylightSavings());
 MqlTick live;ZeroMemory(live);bool quote_ok=SymbolInfoTick("US30Cash",live);
 int clock_file=FileOpen(RUN_ID+"_clock.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 if(clock_file!=INVALID_HANDLE){
  string clock_json="{\"run_id\":\""+RUN_ID+"\",\"time_current\":"+IntegerToString((long)TimeCurrent())+
   ",\"time_trade_server\":"+IntegerToString((long)TimeTradeServer())+",\"time_local\":"+IntegerToString((long)TimeLocal())+
   ",\"time_gmt\":"+IntegerToString((long)TimeGMT())+",\"gmt_offset_seconds\":"+IntegerToString(TimeGMTOffset())+
   ",\"daylight_savings_seconds\":"+IntegerToString(TimeDaylightSavings())+",\"quote_ok\":"+(quote_ok?"true":"false")+
   ",\"quote_time\":"+IntegerToString((long)live.time)+",\"quote_time_msc\":"+IntegerToString(live.time_msc)+",\"orders_sent\":0}";
  FileWriteString(clock_file,clock_json);FileClose(clock_file);
 }
 int f=FileOpen(RUN_ID+"_native.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',',CP_UTF8);
 if(f==INVALID_HANDLE)return;
 FileWrite(f,"fixture","bar_index","bar_time","production_main","native_main","production_d","native_d","production_signal","native_signal","readiness");
 bool ok=true;
 for(int i=0;i<5;i++){if(!RunFixture(i,f)){ok=false;PrintFormat("MAIN_K_PARITY|CASE_ERROR|case=%s|error=%d",CASES[i],GetLastError());break;}}
 FileFlush(f);FileClose(f);
 int result=FileOpen(RUN_ID+"_result.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 if(result!=INVALID_HANDLE){FileWriteString(result,"{\"run_id\":\""+RUN_ID+"\",\"native_execution\":true,\"passed\":"+(ok?"true":"false")+",\"terminal_build\":"+IntegerToString(TerminalInfoInteger(TERMINAL_BUILD))+",\"orders_sent\":0}");FileClose(result);}
 PrintFormat("MAIN_K_PARITY|END|run=%s|passed=%s",RUN_ID,ok?"YES":"NO");
}
