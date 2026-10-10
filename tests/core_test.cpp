#include <cassert>
#include "../mt5/ResearchCore.mqh"
int main() {
 assert(ResearchSignal(20,20.0001)==1);
 assert(ResearchSignal(19,20)==0);
 assert(ResearchSignal(21,22)==0);
 assert(ResearchSignal(80,79.999)==-1);
 assert(ResearchSignal(81,80)==0);
 assert(ResearchSignal(79,78)==0);
 assert(ResearchSignal(10,90)==1);
 assert(ResearchSignal(90,10)==-1);
 assert(ResearchInvert(1)==-1 && ResearchInvert(-1)==1);
 assert(ResearchTickExit(239.999,0,false)==0);
 assert(ResearchTickExit(240,0,false)==2);
 assert(ResearchTickExit(-180,0,false)==1);
 assert(ResearchTickExit(-179.999,0,false)==0);
 assert(ResearchTickExit(0,99,true)==0);
 assert(ResearchTickExit(0,100,true)==3);
 assert(ResearchTickExit(0,100,false)==0);
 assert(ResearchBarExit(0,-180,240,1)==1);
 assert(ResearchBarExit(0,-179,240,1)==2);
 assert(ResearchBarExit(0,-179,239,99)==0);
 assert(ResearchBarExit(0,-179,239,100)==3);
 assert(ResearchBarExit(250,-200,300,1)==2); // known opening gap
 assert(ResearchBarExit(-200,-250,300,1)==1);
 assert(ResearchEntryPrice(1,1000,1002)==1002);
 assert(ResearchEntryPrice(-1,1000,1002)==1000);
 assert(ResearchExitQuote(1,1000,1002)==1000);
 assert(ResearchExitQuote(-1,1000,1002)==1002);
 assert(ResearchPnL(1,1002,1000)==-2);
 assert(ResearchPnL(-1,1000,1002)==-2);
 long cutoff=ResearchSignalCutoff(1704067200);
 assert(cutoff==1704067499999L);
 assert(ResearchEntryAfterSignal(cutoff,1704067500,1704067500123L));
 assert(!ResearchEntryAfterSignal(cutoff,1704067200,1704067499000L));
 assert(!ResearchEntryAfterSignal(cutoff,1704067500,1704067800000L));
 assert(ResearchGrowLeft(10,10));
 assert(!ResearchGrowLeft(9,10));
}
