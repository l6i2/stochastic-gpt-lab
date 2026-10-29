#property strict
#property version "1.00"
#property script_show_inputs
#property description "Launch the read-only callback observer on a dedicated chart."

void OnStart()
  {
   if(MQLInfoInteger(MQL_TESTER) ||
      AccountInfoString(ACCOUNT_SERVER)!="XMGlobalSC-MT5 5" ||
      AccountInfoInteger(ACCOUNT_TRADE_MODE)!=ACCOUNT_TRADE_MODE_DEMO ||
      StringFind(TerminalInfoString(TERMINAL_DATA_PATH),"20C285FE08971A9A2E814AAC44AFC9D2")<0 ||
      !TerminalInfoInteger(TERMINAL_CONNECTED))
     {Print("PROSPECTIVE_LAUNCH|REFUSED|pinned connected XM demo required");return;}
   if(TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
     {Print("PROSPECTIVE_LAUNCH|REFUSED|Algo Trading must remain disabled");return;}
   for(long id=ChartFirst();id>=0;id=ChartNext(id))
      if(StringFind(ChartGetString(id,CHART_EXPERT_NAME),"ProspectiveUtcObserver")>=0)
        {Print("PROSPECTIVE_LAUNCH|ALREADY_ATTACHED|runtime evidence requires monitor");return;}
   long dedicated=ChartOpen("US30Cash",PERIOD_M1);
   if(dedicated==0)
     {PrintFormat("PROSPECTIVE_LAUNCH|CHART_OPEN_FAILED|error=%d",GetLastError());return;}
   if(!ChartApplyTemplate(dedicated,"\\Profiles\\Templates\\PC_A_ProspectiveUtcObserver.tpl"))
     {PrintFormat("PROSPECTIVE_LAUNCH|TEMPLATE_QUEUE_FAILED|error=%d",GetLastError());return;}
   PrintFormat("PROSPECTIVE_LAUNCH|QUEUED_NOT_CERTIFIED|chart=%I64d|wait for native SESSION_START and callbacks",dedicated);
  }
