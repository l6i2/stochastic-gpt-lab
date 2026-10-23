#property strict

void OnStart()
  {
   const string symbol = "US30Cash";
   string days[7] = {"SUNDAY", "MONDAY", "TUESDAY", "WEDNESDAY",
                    "THURSDAY", "FRIDAY", "SATURDAY"};
   long selected = 0;
   bool symbol_exists = SymbolInfoInteger(symbol, SYMBOL_SELECT, selected);
   datetime server_now = TimeTradeServer();
   datetime utc_now = TimeGMT();

   PrintFormat("XM_SESSION_PROBE|START|symbol=%s|symbol_selected=%s|server=%s",
               symbol, symbol_exists && selected != 0 ? "YES" : "NO",
               AccountInfoString(ACCOUNT_SERVER));
   PrintFormat("XM_SESSION_PROBE|CLOCK|server_time=%s|utc_time=%s|offset_seconds=%I64d",
               TimeToString(server_now, TIME_DATE|TIME_SECONDS),
               TimeToString(utc_now, TIME_DATE|TIME_SECONDS),
               (long)(server_now - utc_now));

   for(int day = 0; day < 7; day++)
     {
      for(uint index = 0; index < 16; index++)
        {
         datetime from_time = 0;
         datetime to_time = 0;
         if(!SymbolInfoSessionQuote(symbol, (ENUM_DAY_OF_WEEK)day, index,
                                    from_time, to_time))
            break;
         PrintFormat("XM_SESSION_PROBE|QUOTE|day=%s|index=%u|from=%s|to=%s",
                     days[day], index, TimeToString(from_time, TIME_MINUTES),
                     TimeToString(to_time, TIME_MINUTES));
        }
      for(uint index = 0; index < 16; index++)
        {
         datetime from_time = 0;
         datetime to_time = 0;
         if(!SymbolInfoSessionTrade(symbol, (ENUM_DAY_OF_WEEK)day, index,
                                    from_time, to_time))
            break;
         PrintFormat("XM_SESSION_PROBE|TRADE|day=%s|index=%u|from=%s|to=%s",
                     days[day], index, TimeToString(from_time, TIME_MINUTES),
                     TimeToString(to_time, TIME_MINUTES));
        }
     }

   Print("XM_SESSION_PROBE|END");
  }
