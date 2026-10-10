#ifndef STOCHASTIC_RESEARCH_CORE
#define STOCHASTIC_RESEARCH_CORE
// Scalar core shared verbatim with the native C++ regression harness.
int ResearchSignal(double previous,double current) {
 if(previous<=20.0&&current>20.0)return 1;
 if(previous>=80.0&&current<80.0)return -1;
 return 0;
}
// 0=active, 1=SL, 2=TP, 3=TIME_EXIT. Opening gaps are resolved first.
int ResearchBarExit(double opening,double worst,double best,int completed_bars) {
 if(opening<=-180.0)return 1;
 if(opening>=240.0)return 2;
 if(worst<=-180.0)return 1;
 if(best>=240.0)return 2;
 if(completed_bars>=100)return 3;
 return 0;
}
int ResearchTickExit(double pnl,int completed_bars,bool boundary) {
 if(pnl<=-180.0)return 1;
 if(pnl>=240.0)return 2;
 if(boundary&&completed_bars>=100)return 3;
 return 0;
}
int ResearchInvert(int side){return -side;}
bool ResearchGrowLeft(double left_weight,double right_weight){return left_weight>=right_weight;}
double ResearchEntryPrice(int side,double bid,double ask){return side==1?ask:bid;}
double ResearchExitQuote(int side,double bid,double ask){return side==1?bid:ask;}
double ResearchPnL(int side,double entry,double exit_price){return side*(exit_price-entry);}
long ResearchSignalCutoff(long bar_open_seconds){return (bar_open_seconds+300)*1000-1;}
bool ResearchEntryAfterSignal(long cutoff,long entry_bar_seconds,long entry_msc){
 return entry_bar_seconds*1000>cutoff&&entry_msc>=entry_bar_seconds*1000&&entry_msc<(entry_bar_seconds+300)*1000;
}
#endif
