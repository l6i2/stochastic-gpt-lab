#include <iostream>
#include <iomanip>
#include <string>
#include "../mt5/HeikinAshiCore.mqh"
int main(int argc,char** argv){
 if(argc!=2)return 2;
 const long cutoff=std::stol(argv[1]);
 HeikinAshiState state;
 long time;double o,h,l,c;
 std::cout<<std::setprecision(17);
 while(std::cin>>time>>o>>h>>l>>c){
  if(!state.Append(time,o,h,l,c,cutoff))continue;
  std::cout<<state.last_time<<","<<state.count<<","<<state.seed_time<<","<<state.bars[0].o<<","<<state.bars[0].c<<","<<state.Ready()<<","<<state.LeftCensored();
  for(int j=0;j<54;j++)std::cout<<","<<state.values[j];
  std::cout<<"\n";
 }
}
