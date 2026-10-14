#property strict
#include "ResearchCore.mqh"
#include "HeikinAshiCore.mqh"
HeikinAshiState ha;
#property version "1.10"
#property description "Research only: causal M5 stochastic events, counterfactuals, and intratrade snapshots."
// No trading API is used anywhere in this project.
enum TriggerLine { MAIN_K=0, SIGNAL_D=1 };
enum SimulationMode { TICK_QUOTES=0, BAR_CONSERVATIVE=1 };
enum ProfileWeight { TICK_ACTIVITY=0, REAL_TRADE_VOLUME=1 };
enum BrokerDST { DST_NONE=0, DST_EU=1, DST_US=2 };
input bool LIVE_TRADING=false;
input string ResearchSymbol=""; // empty = tester symbol, e.g. US30Cash
input TriggerLine trigger_line=MAIN_K;
input SimulationMode simulation_mode=TICK_QUOTES;
input bool ConfirmRealTickTesterMode=false;
input ProfileWeight profile_weight=TICK_ACTIVITY;
input double ProfileBinSize=10.0; // absolute price units, fixed origin zero
input int ProfileMaxBins=20000;
input int SessionStartServerHour=0;
input int ServerUTCOffsetWinterHours=2;
input BrokerDST ServerDSTRule=DST_EU;
input string OutputFile="stochastic_events.csv";
input string SnapshotOutputFile="intratrade_snapshots.csv";
input string TargetOutputFile="intratrade_snapshot_targets.csv";
const int K_PERIOD=5,D_PERIOD=3,SLOWING=3,TIME_EXIT_BARS=100;
const double OVERSOLD=20.0,OVERBOUGHT=80.0,TP_DISTANCE=240.0,SL_DISTANCE=180.0;
string sym,header="",row=""; bool defining=false,failed=false;
int out=INVALID_HANDLE,snapshot_out=INVALID_HANDLE,target_out=INVALID_HANDLE,stoch=INVALID_HANDLE,atr=INVALID_HANDLE,ema[4]={INVALID_HANDLE,INVALID_HANDLE,INVALID_HANDLE,INVALID_HANDLE};
int periods[4]={20,50,100,200};
datetime last_bar=0; long serial=0; int next_write=0; int rows_written=0,snapshots_written=0,targets_written=0,snapshot_skipped=0;bool snapshot_failed=false;
MqlRates rates[]; double kval[],dval[],av[],ev0[],ev1[],ev2[],ev3[];
struct VirtualTrade { int side; double entry,exit_price,mfe,mae; long entry_bar,entry_msc,exit_msc,signal_msc; int bars; string reason,signal_id,mode; bool done; bool snapshot_done[9]; };
struct Event { string features; VirtualTrade follow; VirtualTrade invert; };
struct SnapshotRef { string snapshot_id,signal_id,mode; int side,snapshot_bar; double pnl,mfe,mae; };
Event events[];
SnapshotRef snapshot_refs[];
string snapshot_header="",snapshot_row="",target_header="";
double last_bid=0,last_ask=0; long last_quote_msc=0; bool have_last_quote=false;
int snapshot_offsets[9]={1,2,3,5,10,15,20,30,50};
long cached_profile_cutoff=-1;string cached_profile_header="",cached_profile_row="";
// Preserve enough precision that strict Stochastic threshold crossings survive CSV round-trips.
string Num(double x) { if(!MathIsValidNumber(x)||x==EMPTY_VALUE) return ""; return DoubleToString(x,16); }
void S(string key,string value) { if(defining) header+=(header==""?"":",")+key; row+=(row==""?"":",")+value; }
void N(string key,double value) { S(key,Num(value)); }
void I(string key,long value) { S(key,IntegerToString(value)); }
double Ratio(double a,double b) { return b==0.0||b==EMPTY_VALUE||a==EMPTY_VALUE?EMPTY_VALUE:a/b; }
double Diff(double a,double b) { return a==EMPTY_VALUE||b==EMPTY_VALUE?EMPTY_VALUE:a-b; }
double Mean(double &a[],int start,int n) { if(start+n>ArraySize(a)) return EMPTY_VALUE; double s=0; for(int i=start;i<start+n;i++){if(a[i]==EMPTY_VALUE)return EMPTY_VALUE;s+=a[i];} return s/n; }
double SD(double &a[],int start,int n) { double m=Mean(a,start,n); if(m==EMPTY_VALUE)return EMPTY_VALUE; double s=0;for(int i=start;i<start+n;i++)s+=(a[i]-m)*(a[i]-m);return MathSqrt(s/n); }
double Rank(double &a[],int n) { if(ArraySize(a)<n||a[0]==EMPTY_VALUE)return EMPTY_VALUE;int count=0;for(int i=0;i<n;i++){if(a[i]==EMPTY_VALUE)return EMPTY_VALUE;if(a[i]<=a[0])count++;}return 100.0*count/n; }
void Fatal(string message) { failed=true; Print("FATAL RESEARCH RUN: ",message); ExpertRemove(); }
int NthSunday(int year,int month,int nth) { MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=1;TimeToStruct(StructToTime(d),d);return 1+(7-d.day_of_week)%7+7*(nth-1); }
datetime DateAt(int year,int month,int day,int hour) { MqlDateTime d;ZeroMemory(d);d.year=year;d.mon=month;d.day=day;d.hour=hour;return StructToTime(d); }
int LastSunday(int year,int month) { datetime next=DateAt(year,month+1,1,0);MqlDateTime d;TimeToStruct(next-86400,d);return d.day-d.day_of_week; }
bool USDST(datetime utc) { MqlDateTime d;TimeToStruct(utc,d);return utc>=DateAt(d.year,3,NthSunday(d.year,3,2),7)&&utc<DateAt(d.year,11,NthSunday(d.year,11,1),6); }
bool IsBrokerDST(datetime utc) { if(ServerDSTRule==DST_NONE)return false;if(ServerDSTRule==DST_US)return USDST(utc); MqlDateTime d;TimeToStruct(utc,d);return utc>=DateAt(d.year,3,LastSunday(d.year,3),1)&&utc<DateAt(d.year,10,LastSunday(d.year,10),1); }
datetime ToUTC(datetime server) { datetime guess=server-ServerUTCOffsetWinterHours*3600;return guess-(IsBrokerDST(guess)?3600:0); }
void TimeFeatures(datetime signal) {
 datetime utc=ToUTC(signal),ny=utc+(USDST(utc)?-4:-5)*3600; MqlDateTime d;TimeToStruct(ny,d);
 S("server_time",TimeToString(signal,TIME_DATE|TIME_SECONDS));S("UTC_time",TimeToString(utc,TIME_DATE|TIME_SECONDS));S("NY_time",TimeToString(ny,TIME_DATE|TIME_SECONDS));
 I("signal_utc_epoch",(long)utc);I("NY_hour",d.hour);I("NY_minute",d.min);I("weekday",(d.day_of_week+6)%7);
 // Non-overlapping descriptive buckets in NY local time, not exchange calendars.
 S("session",d.hour>=8&&d.hour<17?"New_York":d.hour>=3&&d.hour<8?"London":d.hour>=19||d.hour<3?"Asia":"Other");
 I("server_utc_offset_seconds",(long)(signal-utc));
}
void MissingProfile(string p,string status,long from,long to,int error) {
 S(p+"status",status);S(p+"source",profile_weight==TICK_ACTIVITY?"tick_activity_bid":"real_trade_volume_last");I(p+"window_start_msc",from);I(p+"window_end_msc",to);I(p+"copy_error",error);
 string names[]={"ticks_used","first_tick_msc","last_tick_msc","POC","VAH","VAL","distance_price_to_POC","distance_price_to_VAH","distance_price_to_VAL","inside_value_area","above_value_area","below_value_area","POC_position_in_range","high_volume_node_nearest","low_volume_node_nearest","distance_to_HVN","distance_to_LVN"};
 for(int i=0;i<ArraySize(names);i++)S(p+names[i],"");
}
void Profile(string p,long from,long to,double price) {
 if(from>to){MissingProfile(p,"empty_window",from,to,0);return;}
 long keys[];double weights[];int size=0,err=0;long used=0,first=0,last=0;bool bad=false;
 // Hour chunks keep tick memory bounded; every query is inclusive and non-overlapping.
 for(long start=from;start<=to;start+=3600000) {
  MqlTick ticks[];long end=(long)MathMin((double)to,(double)(start+3599999));ResetLastError();
  int n=CopyTicksRange(sym,ticks,COPY_TICKS_ALL,(ulong)start,(ulong)end);err=GetLastError();
  if(n<0||err!=0){bad=true;break;}
  for(int j=0;j<n;j++) {
   if(ticks[j].time_msc<from||ticks[j].time_msc>to){bad=true;err=-1;break;}
   double px=ticks[j].bid,w=1.0;
   if(profile_weight==REAL_TRADE_VOLUME) { if((ticks[j].flags&(TICK_FLAG_LAST|TICK_FLAG_VOLUME|TICK_FLAG_BUY|TICK_FLAG_SELL))==0||ticks[j].volume_real<=0||ticks[j].last<=0)continue;px=ticks[j].last;w=ticks[j].volume_real; }
   if(px<=0)continue;long key=(long)MathFloor(px/ProfileBinSize);int lo=0,hi=size;
   while(lo<hi){int mid=(lo+hi)/2;if(keys[mid]<key)lo=mid+1;else hi=mid;}
   if(lo==size||keys[lo]!=key){if(size>=ProfileMaxBins){bad=true;err=-2;break;}ArrayResize(keys,size+1);ArrayResize(weights,size+1);for(int q=size;q>lo;q--){keys[q]=keys[q-1];weights[q]=weights[q-1];}keys[lo]=key;weights[lo]=0;size++;}
   weights[lo]+=w;if(used==0)first=ticks[j].time_msc;last=ticks[j].time_msc;used++;
  }
  if(bad)break;
 }
 if(bad||size==0){MissingProfile(p,bad?"copy_error_or_limit":"no_eligible_ticks",from,to,err);return;}
 // Include zero-activity bins between extremes to identify low-volume nodes honestly.
 long span=keys[size-1]-keys[0]+1;
 if(span>ProfileMaxBins){MissingProfile(p,"bin_limit",from,to,-2);return;}
 double w[];ArrayResize(w,(int)span);ArrayInitialize(w,0);for(int j=0;j<size;j++)w[(int)(keys[j]-keys[0])]=weights[j];
 int poc=0;double total=0;for(int j=0;j<(int)span;j++){total+=w[j];if(w[j]>w[poc])poc=j;}
 int left=poc,right=poc;double mass=w[poc];
 while(mass<0.70*total&&(left>0||right<span-1)) { double lw=left>0?w[left-1]:-1,rw=right<span-1?w[right+1]:-1;if(ResearchGrowLeft(lw,rw)){left--;mass+=w[left];}else{right++;mass+=w[right];} }
 double pocp=(keys[0]+poc+0.5)*ProfileBinSize,val=(keys[0]+left)*ProfileBinSize,vah=(keys[0]+right+1)*ProfileBinSize;
 double hv=EMPTY_VALUE,lv=EMPTY_VALUE,hd=DBL_MAX,ld=DBL_MAX;
 for(int j=0;j<(int)span;j++){double center=(keys[0]+j+0.5)*ProfileBinSize,dist=MathAbs(price-center);double a=j>0?w[j-1]:w[j],b=j<span-1?w[j+1]:w[j];
  if(w[j]>=a&&w[j]>=b&&w[j]>0&&dist<hd){hv=center;hd=dist;}
  if(w[j]<=a&&w[j]<=b&&(w[j]<a||w[j]<b)&&dist<ld){lv=center;ld=dist;}
 }
 S(p+"status","available_coverage_unverified");S(p+"source",profile_weight==TICK_ACTIVITY?"tick_activity_bid":"real_trade_volume_last");I(p+"window_start_msc",from);I(p+"window_end_msc",to);I(p+"copy_error",0);
 I(p+"ticks_used",used);I(p+"first_tick_msc",first);I(p+"last_tick_msc",last);N(p+"POC",pocp);N(p+"VAH",vah);N(p+"VAL",val);
 N(p+"distance_price_to_POC",price-pocp);N(p+"distance_price_to_VAH",price-vah);N(p+"distance_price_to_VAL",price-val);
 I(p+"inside_value_area",price>=val&&price<=vah);I(p+"above_value_area",price>vah);I(p+"below_value_area",price<val);N(p+"POC_position_in_range",(poc+0.5)/span);
 N(p+"high_volume_node_nearest",hv);N(p+"low_volume_node_nearest",lv);N(p+"distance_to_HVN",Diff(price,hv));N(p+"distance_to_LVN",Diff(price,lv));
}
void EMAFeatures(string suffix,double &a[]) { N("price_to_ema"+suffix,Diff(rates[0].close,a[0]));N("ema"+suffix+"_slope",Diff(a[0],a[1])); }
void UpdateHA(long cutoff) {
 // Called for EVERY closed bar, including bars without a Stochastic signal.
 // First call seeds once using available prehistory (up to 350 closed bars).
 for(int j=ArraySize(rates)-1;j>=0;j--) {
  if(ha.count>0&&(long)rates[j].time<=ha.last_time)continue;
  ha.Append((long)rates[j].time,rates[j].open,rates[j].high,rates[j].low,rates[j].close,cutoff);
 }
}
void HAFeatures(long cutoff) {
 bool aligned=ha.count>0&&ha.last_time==(long)rates[0].time&&
              (ha.last_time+300)*1000-1<=cutoff;
 S("ha_status",!aligned?"unavailable":ha.Ready()?"ready":"warming_up");
 I("ha_seed_bar_open",ha.seed_time);I("ha_last_bar_open",ha.last_time);
 I("ha_bars_processed",ha.count);I("ha_warmup_bars",HA_WARMUP);
 I("ha_streak_left_censored",ha.LeftCensored());
 string names[]={"ha_open","ha_high","ha_low","ha_close","ha_direction","ha_body","ha_range","ha_body_percent","ha_upper_wick","ha_lower_wick","ha_upper_wick_to_range","ha_lower_wick_to_range","ha_delta_close_1","ha_delta_close_2","ha_delta_close_3","ha_delta_body_1","ha_delta_body_2","ha_delta_body_3","ha_body_expansion","ha_range_expansion","ha_consecutive_bullish","ha_consecutive_bearish","ha_bullish_ratio_3","ha_bullish_ratio_5","ha_bullish_ratio_10","ha_bullish_ratio_20","ha_bearish_ratio_3","ha_bearish_ratio_5","ha_bearish_ratio_10","ha_bearish_ratio_20","ha_avg_body_3","ha_avg_body_5","ha_avg_body_10","ha_avg_body_20","ha_avg_range_3","ha_avg_range_5","ha_avg_range_10","ha_avg_range_20","ha_body_vs_avg5","ha_body_vs_avg10","ha_range_vs_avg5","ha_range_vs_avg10","ha_no_lower_wick","ha_no_upper_wick","ha_small_body","ha_bullish_strong","ha_bearish_strong","ha_indecision","ha_changed_to_bullish","ha_changed_to_bearish","ha_bullish_after_bearish_run","ha_bearish_after_bullish_run","ha_bullish_run_before_signal","ha_bearish_run_before_signal"};
 for(int j=0;j<ArraySize(names);j++)N(names[j],aligned&&ha.Ready()?ha.values[j]:EMPTY_VALUE);
}
bool SnapHasKey(string key){string keys[];int n=StringSplit(snapshot_header,',',keys);for(int j=0;j<n;j++)if(keys[j]==key)return true;return false;}
void SnapField(string key,string value){if(snapshot_header=="")snapshot_header=key;else if(!SnapHasKey(key))snapshot_header+=","+key;snapshot_row+=(snapshot_row==""?"":",")+value;}
void SnapS(string key,string value){SnapField(key,value);}
void SnapN(string key,double value){SnapField(key,Num(value));}
void SnapI(string key,long value){SnapField(key,IntegerToString(value));}
void SnapProfile(string prefix,long from,long to,double price){string oh=header,orr=row;bool od=defining;header="";row="";defining=true;Profile(prefix,from,to,price);string ph=header,pr=row;header=oh;row=orr;defining=od;if(ph!=""){if(snapshots_written==0){if(snapshot_header=="")snapshot_header=ph;else snapshot_header+=","+ph;}snapshot_row+=(snapshot_row==""?"":",")+pr;}}
void SnapProfileFields(long cutoff,double price){if(cached_profile_cutoff==cutoff){if(cached_profile_row!="")snapshot_row+=(snapshot_row==""?"":",")+cached_profile_row;return;}int h=StringLen(snapshot_header),r=StringLen(snapshot_row),mins[4]={30,60,120,240};for(int j=0;j<4;j++)SnapProfile("vp_"+IntegerToString(mins[j])+"m_",cutoff+1-(long)mins[j]*60000,cutoff,price);MqlDateTime dt;TimeToStruct((datetime)(cutoff/1000),dt);dt.hour=SessionStartServerHour;dt.min=0;dt.sec=0;datetime session=StructToTime(dt);if(session>cutoff/1000)session-=86400;SnapProfile("vp_session_",(long)session*1000,cutoff,price);cached_profile_cutoff=cutoff;cached_profile_header=StringSubstr(snapshot_header,h+(h>0?1:0));cached_profile_row=StringSubstr(snapshot_row,r+(r>0?1:0));}
void SnapHA(){string names[]={"ha_open","ha_high","ha_low","ha_close","ha_direction","ha_body","ha_range","ha_body_percent","ha_upper_wick","ha_lower_wick","ha_upper_wick_to_range","ha_lower_wick_to_range","ha_delta_close_1","ha_delta_close_2","ha_delta_close_3","ha_delta_body_1","ha_delta_body_2","ha_delta_body_3","ha_body_expansion","ha_range_expansion","ha_consecutive_bullish","ha_consecutive_bearish","ha_bullish_ratio_3","ha_bullish_ratio_5","ha_bullish_ratio_10","ha_bullish_ratio_20","ha_bearish_ratio_3","ha_bearish_ratio_5","ha_bearish_ratio_10","ha_bearish_ratio_20","ha_avg_body_3","ha_avg_body_5","ha_avg_body_10","ha_avg_body_20","ha_avg_range_3","ha_avg_range_5","ha_avg_range_10","ha_avg_range_20","ha_body_vs_avg5","ha_body_vs_avg10","ha_range_vs_avg5","ha_range_vs_avg10","ha_no_lower_wick","ha_no_upper_wick","ha_small_body","ha_bullish_strong","ha_bearish_strong","ha_indecision","ha_changed_to_bullish","ha_changed_to_bearish","ha_bullish_after_bearish_run","ha_bearish_after_bullish_run","ha_bullish_run_before_signal","ha_bearish_run_before_signal"};bool ready=ha.count>0&&ha.last_time==(long)rates[0].time&&ha.Ready();SnapS("ha_status",ready?"ready":ha.count>0&&ha.last_time==(long)rates[0].time?"warming_up":"unavailable");for(int j=0;j<ArraySize(names);j++)SnapN(names[j],ready?ha.values[j]:EMPTY_VALUE);}
void SnapTime(long cutoff){datetime server=(datetime)(cutoff/1000),utc=ToUTC(server),ny=utc+(USDST(utc)?-4:-5)*3600;MqlDateTime d;TimeToStruct(ny,d);SnapS("server_time",TimeToString(server,TIME_DATE|TIME_SECONDS));SnapS("UTC_time",TimeToString(utc,TIME_DATE|TIME_SECONDS));SnapS("NY_time",TimeToString(ny,TIME_DATE|TIME_SECONDS));SnapI("NY_hour",d.hour);SnapI("weekday",(d.day_of_week+6)%7);SnapS("session",d.hour>=8&&d.hour<17?"New_York":d.hour>=3&&d.hour<8?"London":d.hour>=19||d.hour<3?"Asia":"Other");}
void SnapshotTrade(VirtualTrade &t,int snapshot_bar){
 if(t.done||!have_last_quote)return;long cutoff=((long)rates[0].time+300)*1000-1;double bid=last_bid,ask=last_ask,spread=ask-bid,mark=ResearchExitQuote(t.side,bid,ask),pnl=ResearchPnL(t.side,t.entry,mark);if(last_quote_msc>cutoff||bid<=0||ask<bid){snapshot_failed=true;Print("INTRATRADE SNAPSHOT MARK OUTSIDE CUTOFF");return;}string id=t.signal_id+"_"+t.mode+"_"+IntegerToString(snapshot_bar);snapshot_row="";
 SnapS("snapshot_id",id);SnapS("signal_id",t.signal_id);SnapS("symbol",sym);SnapI("signal_time_msc",t.signal_msc);SnapS("original_signal",t.mode=="FOLLOW"?(t.side==1?"BUY":"SELL"):(t.side==-1?"BUY":"SELL"));SnapS("virtual_mode",t.mode);SnapS("virtual_side",t.side==1?"BUY":"SELL");SnapI("entry_time_msc",t.entry_msc);SnapI("snapshot_bar",snapshot_bar);SnapI("snapshot_time_msc",cutoff);SnapI("feature_max_time_msc",cutoff);SnapI("mark_time_msc",last_quote_msc);
 SnapN("current_bid",bid);SnapN("current_ask",ask);SnapN("spread",spread);SnapN("current_unrealized_pnl",pnl);SnapN("distance_to_tp",TP_DISTANCE-pnl);SnapN("distance_to_sl",SL_DISTANCE+pnl);SnapN("current_mfe_so_far",t.mfe);SnapN("current_mae_so_far",t.mae);SnapI("bars_open",snapshot_bar);
 SnapN("stoch_k",kval[0]);SnapN("stoch_d",dval[0]);SnapN("stoch_k_prev",kval[1]);SnapN("stoch_d_prev",dval[1]);SnapN("stoch_k_slope_1",Diff(kval[0],kval[1]));SnapN("stoch_k_slope_3",(kval[0]-kval[3])/3.0);SnapN("stoch_d_slope_1",Diff(dval[0],dval[1]));SnapN("stoch_d_slope_3",(dval[0]-dval[3])/3.0);SnapN("stoch_k_minus_d",kval[0]-dval[0]);SnapS("stoch_zone",kval[0]<=20?"OVERSOLD":kval[0]>=80?"OVERBOUGHT":"NEUTRAL");SnapI("stoch_reentered_oversold",kval[0]<=20&&kval[1]>20);SnapI("stoch_reentered_overbought",kval[0]>=80&&kval[1]<80);SnapN("stoch_distance_to_opposite_zone",t.side==1?80-kval[0]:kval[0]-20);SnapI("stoch_direction_change",(kval[0]-kval[1])*(kval[1]-kval[2])<0);
 double vol[],ranges[],closes[];int n=ArraySize(rates);ArrayResize(vol,n);ArrayResize(ranges,n);ArrayResize(closes,n);for(int j=0;j<n;j++){vol[j]=(double)rates[j].tick_volume;ranges[j]=rates[j].high-rates[j].low;closes[j]=rates[j].close;}SnapI("tick_volume",rates[0].tick_volume);SnapI("real_volume",rates[0].real_volume);int vw[4]={5,10,20,50};for(int j=0;j<4;j++)SnapN("relative_volume_"+IntegerToString(vw[j]),Ratio(vol[0],Mean(vol,1,vw[j])));SnapN("volume_change_1",Diff(Ratio(vol[0],vol[1]),1));SnapN("volume_change_3",Diff(Ratio(vol[0],vol[3]),1));SnapN("volume_zscore_20",Ratio(Diff(vol[0],Mean(vol,1,20)),SD(vol,1,20)));SnapN("volume_zscore_50",Ratio(Diff(vol[0],Mean(vol,1,50)),SD(vol,1,50)));SnapN("volume_expansion",Ratio(vol[0],Mean(vol,1,20)));
 SnapN("open",rates[0].open);SnapN("high",rates[0].high);SnapN("low",rates[0].low);SnapN("close",rates[0].close);SnapN("body",MathAbs(rates[0].close-rates[0].open));SnapN("range",ranges[0]);SnapN("upper_wick",rates[0].high-MathMax(rates[0].open,rates[0].close));SnapN("lower_wick",MathMin(rates[0].open,rates[0].close)-rates[0].low);SnapN("return_1",Ratio(rates[0].close-rates[1].close,rates[1].close));SnapN("return_3",Ratio(rates[0].close-rates[3].close,rates[3].close));SnapN("return_5",Ratio(rates[0].close-rates[5].close,rates[5].close));SnapN("momentum_3",rates[0].close-rates[3].close);SnapN("momentum_5",rates[0].close-rates[5].close);SnapN("ATR",av[0]);SnapN("ATR_percentile_20",Rank(av,20));SnapN("rolling_std_20",SD(closes,0,20));SnapN("rolling_std_50",SD(closes,0,50));SnapN("range_expansion",Ratio(ranges[0],Mean(ranges,1,20)));int hh=0,hl=0,lh=0,ll=0;double high20=-DBL_MAX,low20=DBL_MAX;for(int j=0;j<20;j++){high20=MathMax(high20,rates[j].high);low20=MathMin(low20,rates[j].low);if(j+1<20){if(rates[j].high>rates[j+1].high)hh++;if(rates[j].low>rates[j+1].low)hl++;if(rates[j].high<rates[j+1].high)lh++;if(rates[j].low<rates[j+1].low)ll++;}}SnapI("HH_count_20",hh);SnapI("HL_count_20",hl);SnapI("LH_count_20",lh);SnapI("LL_count_20",ll);SnapN("distance_to_recent_high",rates[0].close-high20);SnapN("distance_to_recent_low",rates[0].close-low20);SnapI("recent_high_break",rates[0].high>high20);SnapI("recent_low_break",rates[0].low<low20);
 SnapN("EMA20",ev0[0]);SnapN("EMA50",ev1[0]);SnapN("EMA100",ev2[0]);SnapN("EMA200",ev3[0]);SnapN("ema20_slope",Diff(ev0[0],ev0[1]));SnapN("ema50_slope",Diff(ev1[0],ev1[1]));SnapN("ema100_slope",Diff(ev2[0],ev2[1]));SnapN("ema200_slope",Diff(ev3[0],ev3[1]));SnapN("price_to_ema20",rates[0].close-ev0[0]);SnapN("price_to_ema50",rates[0].close-ev1[0]);SnapN("price_to_ema100",rates[0].close-ev2[0]);SnapN("price_to_ema200",rates[0].close-ev3[0]);SnapI("ema_bull_alignment",ev0[0]>ev1[0]&&ev1[0]>ev2[0]&&ev2[0]>ev3[0]);SnapI("ema_bear_alignment",ev0[0]<ev1[0]&&ev1[0]<ev2[0]&&ev2[0]<ev3[0]);
 SnapHA();SnapTime(cutoff);SnapProfileFields(cutoff,rates[0].close);if(snapshots_written==0&&FileWriteString(snapshot_out,snapshot_header+"\r\n")==0){snapshot_failed=true;Print("INTRATRADE SNAPSHOT HEADER WRITE FAILED: ",GetLastError());return;}if(FileWriteString(snapshot_out,snapshot_row+"\r\n")==0){snapshot_failed=true;Print("INTRATRADE SNAPSHOT WRITE FAILED: ",GetLastError());return;}FileFlush(snapshot_out);snapshots_written++;
 int z=ArraySize(snapshot_refs);ArrayResize(snapshot_refs,z+1);snapshot_refs[z].snapshot_id=id;snapshot_refs[z].signal_id=t.signal_id;snapshot_refs[z].mode=t.mode;snapshot_refs[z].side=t.side;snapshot_refs[z].snapshot_bar=snapshot_bar;snapshot_refs[z].pnl=pnl;snapshot_refs[z].mfe=t.mfe;snapshot_refs[z].mae=t.mae;
}
void WriteSnapshotTargets(VirtualTrade &t){if(t.reason=="END_OF_DATA")return;double final_pnl=ResearchPnL(t.side,t.entry,t.exit_price);if(target_header==""){target_header="snapshot_id,signal_id,virtual_mode,snapshot_bar,exit_time_msc,label_status,tp_before_sl_after_snapshot,sl_before_tp_after_snapshot,future_pnl_to_exit,future_max_favorable_move,future_max_adverse_move,profit_erosion,recovery_after_drawdown,continuation_score,reversal_event";if(FileWriteString(target_out,target_header+"\r\n")==0){snapshot_failed=true;Print("INTRATRADE TARGET HEADER WRITE FAILED: ",GetLastError());return;}}for(int j=0;j<ArraySize(snapshot_refs);j++)if(snapshot_refs[j].signal_id==t.signal_id&&snapshot_refs[j].mode==t.mode){double future=final_pnl-snapshot_refs[j].pnl,fm=MathMax(0,t.mfe-snapshot_refs[j].mfe),fa=MathMax(0,t.mae-snapshot_refs[j].mae);string recovery=snapshot_refs[j].pnl<0?(fm>=-snapshot_refs[j].pnl?"1":"0"):"";int reversal=snapshot_refs[j].mfe>=60&&(snapshot_refs[j].mfe-final_pnl>=120||t.reason=="SL");string line=snapshot_refs[j].snapshot_id+","+t.signal_id+","+t.mode+","+IntegerToString(snapshot_refs[j].snapshot_bar)+","+IntegerToString(t.exit_msc)+",COMPLETE,"+(t.reason=="TP"?"1":"0")+","+(t.reason=="SL"?"1":"0")+","+Num(future)+","+Num(fm)+","+Num(fa)+","+Num(MathMax(0,snapshot_refs[j].mfe-final_pnl))+","+recovery+","+Num(future)+","+IntegerToString(reversal)+"\r\n";if(FileWriteString(target_out,line)==0){snapshot_failed=true;Print("INTRATRADE TARGET WRITE FAILED: ",GetLastError());return;}targets_written++;}FileFlush(target_out);}
void EmitSnapshots(){int age;for(int i=next_write;i<ArraySize(events);i++){age=(int)(serial-events[i].follow.entry_bar);if(!events[i].follow.done)for(int j=0;j<9;j++)if(snapshot_offsets[j]==age&&!events[i].follow.snapshot_done[j]){SnapshotTrade(events[i].follow,age);events[i].follow.snapshot_done[j]=true;}age=(int)(serial-events[i].invert.entry_bar);if(!events[i].invert.done)for(int j=0;j<9;j++)if(snapshot_offsets[j]==age&&!events[i].invert.snapshot_done[j]){SnapshotTrade(events[i].invert,age);events[i].invert.snapshot_done[j]=true;}}}
bool Capture(long cutoff,int side,MqlTick &tick) {
 row="";defining=(header=="");datetime signal=(datetime)((cutoff+1)/1000);int n=ArraySize(rates);
 S("signal_id",sym+"_M5_"+IntegerToString(cutoff)+"_"+EnumToString(trigger_line));S("symbol",sym);S("schema_version","1.1");S("trigger_line",EnumToString(trigger_line));
 S("simulation_mode",EnumToString(simulation_mode));I("signal_time_msc",cutoff);I("feature_max_time_msc",cutoff);I("signal_bar_open",(long)rates[0].time);I("entry_bar_open",(long)last_bar);I("entry_time_msc",tick.time_msc);
 I("stoch_k_period",K_PERIOD);I("stoch_d_period",D_PERIOD);I("stoch_slowing",SLOWING);N("tp_distance",TP_DISTANCE);N("sl_distance",SL_DISTANCE);I("time_exit_bars",TIME_EXIT_BARS);
 N("stoch_k",kval[0]);N("stoch_d",dval[0]);N("stoch_k_prev",kval[1]);N("stoch_d_prev",dval[1]);
 double current=trigger_line==MAIN_K?kval[0]:dval[0],previous=trigger_line==MAIN_K?kval[1]:dval[1];
 N("distance_to_20",current-20);N("distance_to_80",current-80);
 for(int j=1;j<=3;j++){N("delta_k_"+IntegerToString(j),Diff(kval[0],kval[j]));N("delta_d_"+IntegerToString(j),Diff(dval[0],dval[j]));}
 int os=0,ob=0;for(int j=1;j<n;j++){double v=trigger_line==MAIN_K?kval[j]:dval[j];if(v==EMPTY_VALUE||v>20)break;os++;}for(int j=1;j<n;j++){double v=trigger_line==MAIN_K?kval[j]:dval[j];if(v==EMPTY_VALUE||v<80)break;ob++;}
 I("bars_in_oversold",os);I("bars_in_overbought",ob);I("zone_run_censored",os==n-1||ob==n-1);N("exit_speed_from_zone",MathAbs(current-previous));
 double vol[],ranges[],closes[];ArrayResize(vol,n);ArrayResize(ranges,n);ArrayResize(closes,n);for(int j=0;j<n;j++){vol[j]=(double)rates[j].tick_volume;ranges[j]=rates[j].high-rates[j].low;closes[j]=rates[j].close;}
 I("history_bars_available",n);I("tick_volume",rates[0].tick_volume);I("real_volume",rates[0].real_volume);S("volume_feature_source","tick_volume");S("real_volume_status",rates[0].real_volume>0?"broker_reported":"zero_or_unavailable");
 int vw[5]={5,10,20,50,100};for(int j=0;j<5;j++)N("relative_volume_"+IntegerToString(vw[j]),Ratio(vol[0],Mean(vol,1,vw[j])));
 int changes[3]={1,3,5};for(int j=0;j<3;j++){int lag=changes[j];N("volume_change_"+IntegerToString(lag),lag<n?Diff(Ratio(vol[0],vol[lag]),1):EMPTY_VALUE);}
 for(int j=2;j<5;j++)N("volume_percentile_"+IntegerToString(vw[j]),Rank(vol,vw[j]));
 N("volume_zscore_20",Ratio(Diff(vol[0],Mean(vol,1,20)),SD(vol,1,20)));N("volume_zscore_50",Ratio(Diff(vol[0],Mean(vol,1,50)),SD(vol,1,50)));N("volume_expansion",Ratio(vol[0],Mean(vol,1,20)));
 N("open",rates[0].open);N("high",rates[0].high);N("low",rates[0].low);N("close",rates[0].close);I("direction",rates[0].close>rates[0].open?1:rates[0].close<rates[0].open?-1:0);
 double body=MathAbs(rates[0].close-rates[0].open);N("body",body);N("range",ranges[0]);N("body_percent",Ratio(100*body,ranges[0]));N("upper_wick",rates[0].high-MathMax(rates[0].open,rates[0].close));N("lower_wick",MathMin(rates[0].open,rates[0].close)-rates[0].low);N("range_to_ATR",Ratio(ranges[0],av[0]));
 for(int q=0;q<3;q++){int w=vw[q],bull=0,bear=0,hh=0,hl=0,lh=0,ll=0;for(int j=0;j<w&&j<n;j++){if(rates[j].close>rates[j].open)bull++;if(rates[j].close<rates[j].open)bear++;if(j+1<n){if(rates[j].high>rates[j+1].high)hh++;if(rates[j].low>rates[j+1].low)hl++;if(rates[j].high<rates[j+1].high)lh++;if(rates[j].low<rates[j+1].low)ll++;}}
  string suffix=IntegerToString(w);N("bullish_ratio_"+suffix,n>=w?(double)bull/w:EMPTY_VALUE);N("bearish_ratio_"+suffix,n>=w?(double)bear/w:EMPTY_VALUE);N("HH_count_"+suffix,n>w?hh:EMPTY_VALUE);N("HL_count_"+suffix,n>w?hl:EMPTY_VALUE);N("LH_count_"+suffix,n>w?lh:EMPTY_VALUE);N("LL_count_"+suffix,n>w?ll:EMPTY_VALUE);
 }
 double hi=-DBL_MAX,lo=DBL_MAX;for(int j=0;j<20&&j<n;j++){hi=MathMax(hi,rates[j].high);lo=MathMin(lo,rates[j].low);}N("distance_to_recent_high",n>=20?rates[0].close-hi:EMPTY_VALUE);N("distance_to_recent_low",n>=20?rates[0].close-lo:EMPTY_VALUE);
 N("ATR",av[0]);N("ATR_normalized",Ratio(av[0],rates[0].close));for(int j=2;j<5;j++)N("ATR_percentile_"+IntegerToString(vw[j]),Rank(av,vw[j]));N("rolling_std_20",SD(closes,0,20));N("rolling_std_50",SD(closes,0,50));N("range_expansion",Ratio(ranges[0],Mean(ranges,1,20)));N("range_compression",Ratio(Mean(ranges,1,20),ranges[0]));
 EMAFeatures("20",ev0);EMAFeatures("50",ev1);EMAFeatures("100",ev2);EMAFeatures("200",ev3);
 N("ema20_minus_50",Diff(ev0[0],ev1[0]));N("ema50_minus_100",Diff(ev1[0],ev2[0]));N("ema100_minus_200",Diff(ev2[0],ev3[0]));
 bool ready=ev0[0]!=EMPTY_VALUE&&ev1[0]!=EMPTY_VALUE&&ev2[0]!=EMPTY_VALUE&&ev3[0]!=EMPTY_VALUE;
 N("bull_alignment",ready?(ev0[0]>ev1[0]&&ev1[0]>ev2[0]&&ev2[0]>ev3[0]?1:0):EMPTY_VALUE);N("bear_alignment",ready?(ev0[0]<ev1[0]&&ev1[0]<ev2[0]&&ev2[0]<ev3[0]?1:0):EMPTY_VALUE);
 HAFeatures(cutoff);
 TimeFeatures(signal);
 int mins[4]={30,60,120,240};for(int j=0;j<4;j++)Profile("vp_"+IntegerToString(mins[j])+"m_",cutoff+1-(long)mins[j]*60000,cutoff,rates[0].close);
 // Session containing the completed bar, so midnight signals retain the session just ended.
 MqlDateTime dt;TimeToStruct((datetime)(cutoff/1000),dt);dt.hour=SessionStartServerHour;dt.min=0;dt.sec=0;datetime start=StructToTime(dt);if(start>cutoff/1000)start-=86400;
 Profile("vp_session_",(long)start*1000,cutoff,rates[0].close);Profile("vp_previous_session_",(long)(start-86400)*1000,(long)start*1000-1,rates[0].close);
 N("entry_bid",tick.bid);N("entry_ask",tick.ask);N("spread",tick.ask-tick.bid);S("follow_side",side==1?"BUY":"SELL");S("invert_side",side==1?"SELL":"BUY");
 S("excursion_quality",simulation_mode==TICK_QUOTES?"observed_quotes":"full_exit_bar_bounds");defining=false;return true;
}
void OpenTrade(VirtualTrade &t,int side,MqlTick &tick,string signal_id,long signal_msc,string mode){t.side=side;t.entry=ResearchEntryPrice(side,tick.bid,tick.ask);t.entry_bar=serial;t.entry_msc=tick.time_msc;t.signal_msc=signal_msc;t.signal_id=signal_id;t.mode=mode;t.done=false;t.reason="";t.mfe=0;t.mae=0;t.bars=0;t.exit_msc=0;t.exit_price=0;for(int j=0;j<9;j++)t.snapshot_done[j]=false;}
void CloseTrade(VirtualTrade &t,double px,long time,string reason,int bars){t.exit_price=px;t.exit_msc=time<t.entry_msc?t.entry_msc:time;t.reason=reason;t.bars=bars;t.done=true;WriteSnapshotTargets(t);}
void Excursion(VirtualTrade &t,double best,double worst){t.mfe=MathMax(t.mfe,best);t.mae=MathMax(t.mae,-worst);}
void TickTrade(VirtualTrade &t,MqlTick &q,bool newbar){
 if(t.done)return;int elapsed=(int)(serial-t.entry_bar);double px=ResearchExitQuote(t.side,q.bid,q.ask),pnl=ResearchPnL(t.side,t.entry,px);int bars=(int)MathMax(1,elapsed+(newbar?0:1));
 int decision=ResearchTickExit(pnl,elapsed,newbar);
 if(decision==1){Excursion(t,pnl,pnl);CloseTrade(t,px,q.time_msc,"SL",bars);return;}
 if(decision==2){Excursion(t,TP_DISTANCE,TP_DISTANCE);CloseTrade(t,t.entry+t.side*TP_DISTANCE,q.time_msc,"TP",bars);return;}
 Excursion(t,pnl,pnl);if(decision==3)CloseTrade(t,px,q.time_msc,"TIME_EXIT",TIME_EXIT_BARS);
}
void BarTrade(VirtualTrade &t,MqlRates &b){
 if(t.done)return;double spread=b.spread*SymbolInfoDouble(sym,SYMBOL_POINT),add=t.side==-1?spread:0;
 double high=b.high+add,low=b.low+add,op=b.open+add;double best=t.side==1?high-t.entry:t.entry-low,worst=t.side==1?low-t.entry:t.entry-high;Excursion(t,best,worst);
 int bars=(int)(serial-t.entry_bar);double sl=t.entry-t.side*SL_DISTANCE,tp=t.entry+t.side*TP_DISTANCE;
 // Gap at the opening quote has known precedence; otherwise ambiguous extremes use SL first.
 double opening=t.side*(op-t.entry);
 int decision=ResearchBarExit(opening,worst,best,bars);
 if(decision==1)CloseTrade(t,opening<=-SL_DISTANCE?op:sl,opening<=-SL_DISTANCE?(long)b.time*1000:(long)(b.time+300)*1000-1,"SL",bars);
 else if(decision==2)CloseTrade(t,tp,opening>=TP_DISTANCE?(long)b.time*1000:(long)(b.time+300)*1000-1,"TP",bars);
 else if(decision==3)CloseTrade(t,b.close+add,(long)(b.time+300)*1000-1,"TIME_EXIT",bars);
}
string TradeCSV(VirtualTrade &t){return Num(t.entry)+","+IntegerToString(t.exit_msc)+","+Num(t.exit_price)+","+t.reason+","+(t.reason=="END_OF_DATA"?"":Num(t.side*(t.exit_price-t.entry)))+","+Num(t.mfe)+","+Num(t.mae)+","+IntegerToString(t.bars);}
string TradeHeader(string p){return p+"entry_price,"+p+"exit_time,"+p+"exit_price,"+p+"exit_reason,"+p+"PnL,"+p+"MFE,"+p+"MAE,"+p+"bars_in_trade";}
void Flush(){while(next_write<ArraySize(events)&&events[next_write].follow.done&&events[next_write].invert.done){
 if(next_write==0)FileWriteString(out,header+","+TradeHeader("follow_")+","+TradeHeader("invert_")+",directional_advantage,run_status\r\n");
 bool complete=events[next_write].follow.reason!="END_OF_DATA"&&events[next_write].invert.reason!="END_OF_DATA";
 double advantage=complete?events[next_write].follow.side*(events[next_write].follow.exit_price-events[next_write].follow.entry)-events[next_write].invert.side*(events[next_write].invert.exit_price-events[next_write].invert.entry):EMPTY_VALUE;
 uint bytes=FileWriteString(out,events[next_write].features+","+TradeCSV(events[next_write].follow)+","+TradeCSV(events[next_write].invert)+","+Num(advantage)+","+(failed?"ABORTED":"OK")+"\r\n");if(bytes==0){failed=true;Print("CSV WRITE FAILED: ",GetLastError());}else rows_written++;events[next_write].features="";next_write++;
 }FileFlush(out);}
bool Buffer(int handle,int buffer,int n,double &a[]){ArraySetAsSeries(a,true);int got=CopyBuffer(handle,buffer,1,n,a);return got==n;}
int OnInit(){
 if(LIVE_TRADING||!MQLInfoInteger(MQL_TESTER)||MQLInfoInteger(MQL_OPTIMIZATION)){Print("Research only: tester required; live and optimization prohibited.");return INIT_FAILED;}
 if(simulation_mode!=TICK_QUOTES||!ConfirmRealTickTesterMode){Print("Intratrade research requires TICK_QUOTES and ConfirmRealTickTesterMode=true.");return INIT_FAILED;}
 if(ProfileBinSize<=0||ProfileMaxBins<2||SessionStartServerHour<0||SessionStartServerHour>23||ServerUTCOffsetWinterHours<-12||ServerUTCOffsetWinterHours>14)return INIT_PARAMETERS_INCORRECT;
 sym=ResearchSymbol==""?_Symbol:ResearchSymbol;if(sym!=_Symbol||StringFind(sym,",")>=0||StringFind(sym,"\"")>=0||StringFind(sym,"\n")>=0||StringFind(sym,"\r")>=0){Print("Select ResearchSymbol as tester symbol; commas prohibited.");return INIT_PARAMETERS_INCORRECT;}
 stoch=iStochastic(sym,PERIOD_M5,K_PERIOD,D_PERIOD,SLOWING,MODE_SMA,STO_LOWHIGH);atr=iATR(sym,PERIOD_M5,14);for(int i=0;i<4;i++)ema[i]=iMA(sym,PERIOD_M5,periods[i],0,MODE_EMA,PRICE_CLOSE);
 if(stoch==INVALID_HANDLE||atr==INVALID_HANDLE)return INIT_FAILED;for(int i=0;i<4;i++)if(ema[i]==INVALID_HANDLE)return INIT_FAILED;
 // Refuse overwrite: a research run must have its own artifact.
 if(FileIsExist(OutputFile)||FileIsExist(OutputFile+".audit.json")||FileIsExist(SnapshotOutputFile)||FileIsExist(SnapshotOutputFile+".audit.json")||FileIsExist(TargetOutputFile)){Print("Output exists. Use unique OutputFile, SnapshotOutputFile, and TargetOutputFile names.");return INIT_FAILED;}
 out=FileOpen(OutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);if(out==INVALID_HANDLE)return INIT_FAILED;
 snapshot_out=FileOpen(SnapshotOutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);if(snapshot_out==INVALID_HANDLE){FileClose(out);out=INVALID_HANDLE;return INIT_FAILED;}
 target_out=FileOpen(TargetOutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);if(target_out==INVALID_HANDLE){FileClose(out);FileClose(snapshot_out);out=INVALID_HANDLE;snapshot_out=INVALID_HANDLE;return INIT_FAILED;}
 last_bar=iTime(sym,PERIOD_M5,0);Print("Research output: ",OutputFile,". PnL in price units; no monetary PnL.");return INIT_SUCCEEDED;
}
void OnTick(){
 if(failed||out==INVALID_HANDLE)return;MqlTick tick;if(!SymbolInfoTick(sym,tick)||tick.bid<=0||tick.ask<tick.bid){Fatal("Invalid execution quote");return;}
 datetime nowbar=iTime(sym,PERIOD_M5,0);bool newbar=nowbar!=last_bar;if(newbar){last_bar=nowbar;serial++;if(simulation_mode==TICK_QUOTES&&ArraySize(events)>next_write){ArraySetAsSeries(rates,true);int sn=CopyRates(sym,PERIOD_M5,1,350,rates);bool ok=sn>=6&&Buffer(stoch,0,sn,kval)&&Buffer(stoch,1,sn,dval)&&Buffer(atr,0,sn,av)&&Buffer(ema[0],0,sn,ev0)&&Buffer(ema[1],0,sn,ev1)&&Buffer(ema[2],0,sn,ev2)&&Buffer(ema[3],0,sn,ev3);if(ok){long sc=ResearchSignalCutoff((long)rates[0].time);UpdateHA(sc);EmitSnapshots();}else{snapshot_failed=true;snapshot_skipped++;Print("INTRATRADE SNAPSHOT SKIPPED: causal context buffers unavailable at ",TimeToString(nowbar,TIME_DATE|TIME_MINUTES));}}}
 if(newbar&&simulation_mode==BAR_CONSERVATIVE){MqlRates b[];if(CopyRates(sym,PERIOD_M5,1,1,b)!=1){Fatal("Missing completed execution bar");return;}for(int i=next_write;i<ArraySize(events);i++){BarTrade(events[i].follow,b[0]);BarTrade(events[i].invert,b[0]);}}
 if(simulation_mode==TICK_QUOTES)for(int i=next_write;i<ArraySize(events);i++){TickTrade(events[i].follow,tick,newbar);TickTrade(events[i].invert,tick,newbar);}
 Flush();last_bid=tick.bid;last_ask=tick.ask;last_quote_msc=tick.time_msc;have_last_quote=true;if(!newbar)return;
 ArraySetAsSeries(rates,true);int n=CopyRates(sym,PERIOD_M5,1,350,rates);if(n<4){Fatal("Insufficient stochastic history; start tester with prehistory");return;}
 UpdateHA(ResearchSignalCutoff((long)rates[0].time));
 if(!Buffer(stoch,0,n,kval)||!Buffer(stoch,1,n,dval)){Fatal("Stochastic history unavailable");return;}
 double current=trigger_line==MAIN_K?kval[0]:dval[0],previous=trigger_line==MAIN_K?kval[1]:dval[1];if(current==EMPTY_VALUE||previous==EMPTY_VALUE){Fatal("Stochastic not initialized");return;}
 int side=ResearchSignal(previous,current);if(side==0)return;
 if(!Buffer(atr,0,n,av)||!Buffer(ema[0],0,n,ev0)||!Buffer(ema[1],0,n,ev1)||!Buffer(ema[2],0,n,ev2)||!Buffer(ema[3],0,n,ev3)){Fatal("Feature buffers unavailable: run is incomplete");return;}
 long cutoff=ResearchSignalCutoff((long)rates[0].time);
 if(!ResearchEntryAfterSignal(cutoff,(long)last_bar,tick.time_msc)){Fatal("Entry chronology mismatch");return;}
 if(!Capture(cutoff,side,tick))return;int index=ArraySize(events);ArrayResize(events,index+1);events[index].features=row;string id=sym+"_M5_"+IntegerToString(cutoff)+"_"+EnumToString(trigger_line);OpenTrade(events[index].follow,side,tick,id,cutoff,"FOLLOW");OpenTrade(events[index].invert,ResearchInvert(side),tick,id,cutoff,"INVERT");
 if(simulation_mode==TICK_QUOTES){TickTrade(events[index].follow,tick,false);TickTrade(events[index].invert,tick,false);}Flush();
}
void Censor(VirtualTrade &t,MqlTick &q){if(t.done)return;CloseTrade(t,t.side==1?q.bid:q.ask,q.time_msc,"END_OF_DATA",(int)MathMax(1,serial-t.entry_bar+1));}
void OnDeinit(const int reason){
 if(out!=INVALID_HANDLE){MqlTick q;ZeroMemory(q);SymbolInfoTick(sym,q);for(int i=next_write;i<ArraySize(events);i++){Censor(events[i].follow,q);Censor(events[i].invert,q);}Flush();FileClose(out);
  int audit=FileOpen(OutputFile+".audit.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);if(audit!=INVALID_HANDLE){FileWriteString(audit,"{\"profile_bin_size\":"+Num(ProfileBinSize)+",\"profile_max_bins\":"+IntegerToString(ProfileMaxBins)+",\"profile_weight\":\""+EnumToString(profile_weight)+"\",\"session_start_server_hour\":"+IntegerToString(SessionStartServerHour)+",\"server_utc_offset_winter_hours\":"+IntegerToString(ServerUTCOffsetWinterHours)+",\"server_dst_rule\":\""+EnumToString(ServerDSTRule)+"\",\"terminal_build\":"+IntegerToString(TerminalInfoInteger(TERMINAL_BUILD))+",\"real_tick_mode_attested\":"+(ConfirmRealTickTesterMode?"true":"false")+",\"schema_version\":\"1.1\",\"signals\":"+IntegerToString(ArraySize(events))+",\"rows_written\":"+IntegerToString(rows_written)+",\"aborted\":"+(failed?"true":"false")+",\"deinit_reason\":"+IntegerToString(reason)+"}");FileClose(audit);}}
  if(snapshot_out!=INVALID_HANDLE){FileFlush(snapshot_out);FileClose(snapshot_out);}if(target_out!=INVALID_HANDLE){FileFlush(target_out);FileClose(target_out);}
  int sa=FileOpen(SnapshotOutputFile+".audit.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);if(sa!=INVALID_HANDLE){FileWriteString(sa,"{\"schema_version\":\"2.0\",\"target_schema_version\":\"1.0\",\"symbol\":\""+sym+"\",\"timeframe\":\"M5\",\"simulation_mode\":\""+EnumToString(simulation_mode)+"\",\"optimization\":\"OFF\",\"LIVE_TRADING\":false,\"signals\":"+IntegerToString(ArraySize(events))+",\"snapshot_rows\":"+IntegerToString(snapshots_written)+",\"target_rows\":"+IntegerToString(targets_written)+",\"snapshot_skipped\":"+IntegerToString(snapshot_skipped)+",\"aborted\":"+((failed||snapshot_failed)?"true":"false")+",\"fatal_or_skip\":"+(snapshot_failed?"\"context_buffers_unavailable\"":"null")+",\"snapshot_schedule\":\"1,2,3,5,10,15,20,30,50\",\"reversal_event_rule\":\"snapshot MFE >= 60 and (snapshot MFE - final PnL >= 120 or exit SL)\",\"deinit_reason\":"+IntegerToString(reason)+"}");FileClose(sa);}
 if(stoch!=INVALID_HANDLE)IndicatorRelease(stoch);if(atr!=INVALID_HANDLE)IndicatorRelease(atr);for(int i=0;i<4;i++)if(ema[i]!=INVALID_HANDLE)IndicatorRelease(ema[i]);
}
