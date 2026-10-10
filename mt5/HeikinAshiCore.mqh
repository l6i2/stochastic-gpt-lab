#ifndef HEIKIN_ASHI_RESEARCH_CORE
#define HEIKIN_ASHI_RESEARCH_CORE
// Portable MQL5/C++ implementation. It has no access to signals or trading APIs.
const int HA_WARMUP=256;
const int HA_READY_BARS=276; // all 20-bar windows begin after the warmup
const double HA_MISSING=1.7976931348623157e308;
double HAAbs(double x){return x<0?-x:x;}
double HAMax(double a,double b){return a>b?a:b;}
double HAMin(double a,double b){return a<b?a:b;}
double HADiv(double a,double b){return b==0?HA_MISSING:a/b;}
struct HABar {
 double o,h,l,c,body,range,upper,lower;
 int direction;
 long bullish,bearish,bull_before,bear_before;
};
class HeikinAshiState {
public:
 HABar bars[21]; // newest first; recurrence itself is never restarted
 long count,seed_time,last_time;
 double values[54];
 HeikinAshiState(){count=0;seed_time=0;last_time=0;}
 bool Ready(){return count>=HA_READY_BARS;}
 bool LeftCensored(){
  if(count==0)return false;
  return bars[0].bullish==count||bars[0].bearish==count||
         (count>1&&(bars[0].bull_before==count-1||bars[0].bear_before==count-1));
 }
 // Reject current/open/future bars and duplicate or out-of-order input.
 bool Append(long bar_time,double o,double h,double l,double c,long cutoff){
  if((bar_time+300)*1000-1>cutoff||(count>0&&bar_time<=last_time))return false;
  HABar b;
  b.c=(o+h+l+c)/4.0;
  b.o=count==0?(o+c)/2.0:(bars[0].o+bars[0].c)/2.0;
  b.h=HAMax(h,HAMax(b.o,b.c));b.l=HAMin(l,HAMin(b.o,b.c));
  b.body=HAAbs(b.c-b.o);b.range=b.h-b.l;
  b.upper=b.h-HAMax(b.o,b.c);b.lower=HAMin(b.o,b.c)-b.l;
  b.direction=b.c>b.o?1:b.c<b.o?-1:0;
  b.bull_before=count==0?0:bars[0].bullish;
  b.bear_before=count==0?0:bars[0].bearish;
  b.bullish=b.direction==1?b.bull_before+1:0;
  b.bearish=b.direction==-1?b.bear_before+1:0;
  for(int j=20;j>0;j--)if(count>=j)bars[j]=bars[j-1];
  bars[0]=b;if(count==0)seed_time=bar_time;last_time=bar_time;count++;
  Calculate();return true;
 }
 double MeanBody(int start,int n){double s=0;for(int j=start;j<start+n;j++)s+=bars[j].body;return s/n;}
 double MeanRange(int start,int n){double s=0;for(int j=start;j<start+n;j++)s+=bars[j].range;return s/n;}
 double DirectionRatio(int side,int n){int s=0;for(int j=0;j<n;j++)if(bars[j].direction==side)s++;return (double)s/n;}
 void Calculate(){
  for(int j=0;j<54;j++)values[j]=HA_MISSING;
  if(!Ready())return;
  HABar b=bars[0];int k=0;
  values[k++]=b.o;values[k++]=b.h;values[k++]=b.l;values[k++]=b.c;
  values[k++]=b.direction;values[k++]=b.body;values[k++]=b.range;
  values[k++]=HADiv(100*b.body,b.range);values[k++]=b.upper;values[k++]=b.lower;
  values[k++]=HADiv(b.upper,b.range);values[k++]=HADiv(b.lower,b.range);
  for(int j=1;j<=3;j++)values[k++]=b.c-bars[j].c;
  for(int j=1;j<=3;j++)values[k++]=b.body-bars[j].body;
  values[k++]=HADiv(b.body,bars[1].body);values[k++]=HADiv(b.range,bars[1].range);
  values[k++]=(double)b.bullish;values[k++]=(double)b.bearish;
  int windows[4]={3,5,10,20};
  for(int j=0;j<4;j++)values[k++]=DirectionRatio(1,windows[j]);
  for(int j=0;j<4;j++)values[k++]=DirectionRatio(-1,windows[j]);
  for(int j=0;j<4;j++)values[k++]=MeanBody(0,windows[j]);
  for(int j=0;j<4;j++)values[k++]=MeanRange(0,windows[j]);
  values[k++]=HADiv(b.body,MeanBody(1,5));values[k++]=HADiv(b.body,MeanBody(1,10));
  values[k++]=HADiv(b.range,MeanRange(1,5));values[k++]=HADiv(b.range,MeanRange(1,10));
  bool no_lower=b.lower<=1e-10,no_upper=b.upper<=1e-10;
  bool small=b.range>0&&b.body<=0.25*b.range;
  values[k++]=no_lower?1:0;values[k++]=no_upper?1:0;values[k++]=small?1:0;
  values[k++]=b.direction==1&&no_lower&&b.body>=0.5*b.range?1:0;
  values[k++]=b.direction==-1&&no_upper&&b.body>=0.5*b.range?1:0;
  values[k++]=small&&b.upper>1e-10&&b.lower>1e-10?1:0;
  values[k++]=b.direction==1&&bars[1].direction!=1?1:0;
  values[k++]=b.direction==-1&&bars[1].direction!=-1?1:0;
  values[k++]=b.direction==1&&b.bear_before>0?1:0;
  values[k++]=b.direction==-1&&b.bull_before>0?1:0;
  values[k++]=(double)b.bull_before;values[k++]=(double)b.bear_before;
 }
};
#endif
