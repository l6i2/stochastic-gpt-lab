// Compiled only as a research script in Scripts/ControllerResearch.
// Execute the EXACT production OnTick and SnapshotTrade code against a synthetic
// MT5 market-data adapter. No historical data, account, or order API is queried.
#property strict
int ProbeCopyRates(string symbol,ENUM_TIMEFRAMES timeframe,int start,int count,MqlRates &result[]);
int ProbeCopyBuffer(int handle,int buffer,int start,int count,double &result[]);
int ProbeCopyTicksRange(string symbol,MqlTick &result[],uint flags,ulong from,ulong to);
bool ProbeSymbolInfoTick(string symbol,MqlTick &result);
datetime ProbeITime(string symbol,ENUM_TIMEFRAMES timeframe,int shift);
void ProbeRemove();
#define CopyRates ProbeCopyRates
#define CopyBuffer ProbeCopyBuffer
#define CopyTicksRange ProbeCopyTicksRange
#define SymbolInfoTick ProbeSymbolInfoTick
#define iTime ProbeITime
#define ExpertRemove ProbeRemove
#define OnInit ProductionOnInit
#define OnTick ProductionOnTick
#define OnDeinit ProductionOnDeinit
#include "..\..\Experts\StochasticIntratradeResearch\StochasticIntratradeResearchEA.mq5"
#undef OnInit
#undef OnTick
#undef OnDeinit
#undef CopyRates
#undef CopyBuffer
#undef CopyTicksRange
#undef SymbolInfoTick
#undef iTime
#undef ExpertRemove

const string PROBE_ID="__PROBE_ID__";
const int PROBE_BARS=560;
const int PROBE_CUTOFF_BAR=450;
MqlRates probe_bars[];
MqlTick probe_ticks[];
int probe_cursor=0;
bool probe_failed=false;

void ProbeRemove(){probe_failed=true;}
datetime ProbeITime(string symbol,ENUM_TIMEFRAMES timeframe,int shift){
 return (datetime)((probe_ticks[probe_cursor].time/300-shift)*300);
}
bool ProbeSymbolInfoTick(string symbol,MqlTick &result){result=probe_ticks[probe_cursor];return true;}
int ProbeBarIndex(){return (int)((ProbeITime("",PERIOD_M5,0)-probe_bars[0].time)/300);}
int ProbeCopyRates(string symbol,ENUM_TIMEFRAMES timeframe,int start,int count,MqlRates &result[]){
 int index=ProbeBarIndex()-start,n=(int)MathMin(count,index+1);ArrayResize(result,n);ArraySetAsSeries(result,true);
 for(int j=0;j<n;j++)result[j]=probe_bars[index-j];return n;
}
double RawK(int index){
 double lo=DBL_MAX,hi=-DBL_MAX;for(int j=0;j<5;j++){lo=MathMin(lo,probe_bars[index-j].low);hi=MathMax(hi,probe_bars[index-j].high);}
 return 100.0*(probe_bars[index].close-lo)/(hi-lo);
}
double ProbeK(int index){return (RawK(index)+RawK(index-1)+RawK(index-2))/3.0;}
int ProbeCopyBuffer(int handle,int buffer,int start,int count,double &result[]){
 int index=ProbeBarIndex()-start;ArrayResize(result,count);ArraySetAsSeries(result,true);
 for(int j=0;j<count;j++){
  int k=index-j;
  if(k<10){result[j]=50;continue;}
  if(handle==1)result[j]=buffer==0?ProbeK(k):(ProbeK(k)+ProbeK(k-1)+ProbeK(k-2))/3.0;
  else if(handle==2){double sum=0;for(int q=0;q<14&&k-q>=0;q++)sum+=probe_bars[k-q].high-probe_bars[k-q].low;result[j]=sum/14;}
  else {int period=handle;double a=2.0/(period+1),value=probe_bars[0].close;for(int q=1;q<=k;q++)value=a*probe_bars[q].close+(1-a)*value;result[j]=value;}
 }return count;
}
int ProbeCopyTicksRange(string symbol,MqlTick &result[],uint flags,ulong from,ulong to){
 ArrayResize(result,0);int n=0;
 // Deliberately expose the entire stream, including future ticks. The exact
 // production Profile query must enforce its own cutoff through from/to.
 for(int j=0;j<ArraySize(probe_ticks);j++)if((ulong)probe_ticks[j].time_msc>=from&&(ulong)probe_ticks[j].time_msc<=to){ArrayResize(result,n+1);result[n++]=probe_ticks[j];}
 return n;
}
void BuildProbe(bool perturb){
 ArrayResize(probe_bars,PROBE_BARS);ArraySetAsSeries(probe_bars,false);ArrayResize(probe_ticks,PROBE_BARS*4);
 datetime first=D'2024.01.08 00:00';
 for(int j=0;j<PROBE_BARS;j++){
  double price=37000+70*MathSin(j*0.31)+20*MathSin(j*0.09);
  if(perturb&&j>PROBE_CUTOFF_BAR)price+=350*MathSin(j*0.73)+220;
  MqlRates b;ZeroMemory(b);b.time=first+j*300;b.open=price-3;b.high=price+9;b.low=price-11;b.close=price+2;b.tick_volume=80+j%17;b.real_volume=0;b.spread=10;
  if(perturb&&j>PROBE_CUTOFF_BAR){b.tick_volume*=9;b.high+=50;b.low-=40;}
  probe_bars[j]=b;
  int offsets[4]={0,60,180,299};
  for(int k=0;k<4;k++){MqlTick t;ZeroMemory(t);t.time=b.time+offsets[k];t.time_msc=(long)t.time*1000;t.bid=k==0?b.open:k==1?b.high:k==2?b.low:b.close;t.ask=t.bid+1;t.flags=TICK_FLAG_BID|TICK_FLAG_ASK;probe_ticks[j*4+k]=t;}
 }
}
void ResetProbe(string suffix){
 failed=false;probe_failed=false;last_bar=probe_bars[350].time;serial=0;next_write=0;rows_written=0;snapshots_written=0;targets_written=0;snapshot_skipped=0;snapshot_failed=false;
 header="";row="";snapshot_header="";snapshot_row="";target_header="";cached_profile_cutoff=-1;cached_profile_header="";cached_profile_row="";
 have_last_quote=false;last_bid=0;last_ask=0;last_quote_msc=0;defining=false;sym="SYNTHETIC_CAUSAL_ONLY";
 ArrayResize(events,0);ArrayResize(snapshot_refs,0);ha.count=0;ha.seed_time=0;ha.last_time=0;
 stoch=1;atr=2;ema[0]=20;ema[1]=50;ema[2]=100;ema[3]=200;
 out=FileOpen(PROBE_ID+"_"+suffix+"_events.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 snapshot_out=FileOpen(PROBE_ID+"_"+suffix+"_snapshots.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 target_out=FileOpen(PROBE_ID+"_"+suffix+"_targets.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 if(out==INVALID_HANDLE||snapshot_out==INVALID_HANDLE||target_out==INVALID_HANDLE)probe_failed=true;
}
void RunProbe(bool perturb,string suffix){
 BuildProbe(perturb);ResetProbe(suffix);
 int tick_dump=FileOpen(PROBE_ID+"_"+suffix+"_input_ticks.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 FileWriteString(tick_dump,"time_msc,bid,ask\r\n");
 for(int j=0;j<ArraySize(probe_ticks);j++)FileWriteString(tick_dump,IntegerToString(probe_ticks[j].time_msc)+","+Num(probe_ticks[j].bid)+","+Num(probe_ticks[j].ask)+"\r\n");FileClose(tick_dump);
 int bar_dump=FileOpen(PROBE_ID+"_"+suffix+"_input_bars.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 FileWriteString(bar_dump,"bar_end_msc,open,high,low,close,tick_volume\r\n");
 for(int j=0;j<ArraySize(probe_bars);j++)FileWriteString(bar_dump,IntegerToString(((long)probe_bars[j].time+300)*1000-1)+","+Num(probe_bars[j].open)+","+Num(probe_bars[j].high)+","+Num(probe_bars[j].low)+","+Num(probe_bars[j].close)+","+IntegerToString(probe_bars[j].tick_volume)+"\r\n");FileClose(bar_dump);
 for(probe_cursor=350*4;probe_cursor<ArraySize(probe_ticks);probe_cursor++){
  ProductionOnTick();if(failed||probe_failed)break;
 }
 probe_cursor=ArraySize(probe_ticks)-1;MqlTick q=probe_ticks[probe_cursor];
 for(int j=next_write;j<ArraySize(events);j++){Censor(events[j].follow,q);Censor(events[j].invert,q);}Flush();
 FileFlush(snapshot_out);FileFlush(target_out);FileClose(out);FileClose(snapshot_out);FileClose(target_out);
 int summary=FileOpen(PROBE_ID+"_"+suffix+"_summary.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
 long cutoff=((long)probe_bars[PROBE_CUTOFF_BAR].time+300)*1000-1;
 FileWriteString(summary,"{\"cutoff\":"+IntegerToString(cutoff)+",\"failed\":"+((failed||probe_failed||snapshot_failed)?"true":"false")+",\"snapshots\":"+IntegerToString(snapshots_written)+",\"events\":"+IntegerToString(ArraySize(events))+"}");FileClose(summary);
}
int OnStart(){
 if(LIVE_TRADING){Print("CAUSAL_PROBE_BLOCKED");return 1;}
 RunProbe(false,"base");RunProbe(true,"future_changed");
 Print("CAUSAL_PROBE_COMPLETE ",PROBE_ID);
 return (failed||probe_failed||snapshot_failed)?1:0;
}
