"""Prepare a versioned every-bar producer; never deploy or launch a terminal."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_NORMALIZED_SHA256 = 'd238c9bdd52aa669cc4e0347ac5f0818ab9b00d498128af8b5f184dac38c075d'


def build(source, destination):
    raw = Path(source).read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != BASE_NORMALIZED_SHA256:
        raise ValueError('Frozen accepted schema 2 producer hash differs; audit before deriving a version')

    def replace(old, new, count=1):
        nonlocal text
        if text.count(old) != count:
            raise ValueError('Source anchor changed: ' + old[:80])
        text = text.replace(old, new)

    schedule = ','.join(map(str, range(1, 101)))
    replace('#property version "1.10"', '#property version "3.00"')
    replace('bool snapshot_done[9]', 'bool snapshot_done[100]')
    replace('int snapshot_offsets[9]={1,2,3,5,10,15,20,30,50};',
            'int snapshot_offsets[100]={' + schedule + '};')
    replace('j<9;', 'j<100;', 3)
    replace('input string TargetOutputFile="intratrade_snapshot_targets.csv";',
            'input string TargetOutputFile="intratrade_snapshot_targets.csv";\n'
            'input string ExecutionQuoteOutputFile="bar_execution_quotes.csv";\n'
            'int execution_out=INVALID_HANDLE,execution_rows=0;MqlTick replay_fill_quote;')
    replace('datetime nowbar=iTime(sym,PERIOD_M5,0);bool newbar=',
            'replay_fill_quote=tick;datetime nowbar=iTime(sym,PERIOD_M5,0);bool newbar=')
    replace('if(snapshot_header=="")snapshot_header=key;else if(!SnapHasKey(key))snapshot_header+=","+key;',
            'if(snapshots_written==0){if(snapshot_header=="")snapshot_header=key;else if(!SnapHasKey(key))snapshot_header+=","+key;}')
    replace('snapshot_row="";\n SnapS("snapshot_id",id);',
            'snapshot_row="";\n if(replay_fill_quote.time_msc<=cutoff){snapshot_failed=true;'
            'Print("BAR REPLAY EXECUTION QUOTE NOT AFTER DECISION");return;}\n SnapS("snapshot_id",id);')
    replace(' int z=ArraySize(snapshot_refs);',
            ' if(execution_rows==0&&FileWriteString(execution_out,"snapshot_id,signal_id,virtual_mode,snapshot_bar,'
            'decision_cutoff_msc,execution_time_msc,execution_bid,execution_ask\\r\\n")==0){snapshot_failed=true;return;}\n'
            ' string execution_line=id+","+t.signal_id+","+t.mode+","+IntegerToString(snapshot_bar)+","+'
            'IntegerToString(cutoff)+","+IntegerToString(replay_fill_quote.time_msc)+","+'
            'Num(replay_fill_quote.bid)+","+Num(replay_fill_quote.ask)+"\\r\\n";\n'
            ' if(FileWriteString(execution_out,execution_line)==0){snapshot_failed=true;return;}'
            'FileFlush(execution_out);execution_rows++;\n int z=ArraySize(snapshot_refs);')
    replace(' last_bar=iTime(sym,PERIOD_M5,0);Print("Research output:',
            ' execution_out=FileOpen(ExecutionQuoteOutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);'
            'if(execution_out==INVALID_HANDLE)return INIT_FAILED;\n last_bar=iTime(sym,PERIOD_M5,0);Print("Research output:')
    replace(' if(stoch!=INVALID_HANDLE)IndicatorRelease(stoch);',
            ' if(execution_out!=INVALID_HANDLE){FileFlush(execution_out);FileClose(execution_out);}\n'
            ' if(stoch!=INVALID_HANDLE)IndicatorRelease(stoch);')
    # Completed trades never need their snapshot references again. Preserve the
    # order of every still-open trade's references and every emitted target.
    replace('targets_written++;}FileFlush(target_out);}',
            'targets_written++;}int kept=0;for(int j=0;j<ArraySize(snapshot_refs);j++)'
            'if(!(snapshot_refs[j].signal_id==t.signal_id&&snapshot_refs[j].mode==t.mode))'
            '{if(kept!=j)snapshot_refs[kept]=snapshot_refs[j];kept++;}'
            'ArrayResize(snapshot_refs,kept);FileFlush(target_out);}')
    replace('bool snapshot_done[100];', 'long replay_entry_quote_index;bool snapshot_done[100];')
    replace('input string ExecutionQuoteOutputFile="bar_execution_quotes.csv";',
            'input string ExecutionQuoteOutputFile="bar_execution_quotes.csv";\n'
            'input string QuotePathOutputFile="bar_quote_path.bin";\n'
            'input string TradeIndexOutputFile="bar_trade_index.csv";\n'
            'int replay_quote_out=INVALID_HANDLE,replay_trade_out=INVALID_HANDLE;\n'
            'long replay_quote_index=-1,replay_quotes_written=0,replay_trades_written=0;')
    replace('execution_bid,execution_ask\\r\\n', 'execution_bid,execution_ask,decision_quote_index\\r\\n')
    replace('Num(replay_fill_quote.ask)+"\\r\\n";',
            'Num(replay_fill_quote.ask)+","+IntegerToString(replay_quote_index)+"\\r\\n";')
    replace('replay_fill_quote=tick;datetime nowbar=',
            'if(!RecordReplayQuote(tick,(int)serial+(iTime(sym,PERIOD_M5,0)!=last_bar?1:0)))return;'
            'replay_fill_quote=tick;datetime nowbar=')
    replace('if(newbar){last_bar=nowbar;serial++;',
            'if(newbar){FileFlush(replay_quote_out);last_bar=nowbar;serial++;')
    replace('string mode){t.side=side;',
            'string mode){t.replay_entry_quote_index=replay_quote_index;t.side=side;')
    replace('t.done=true;WriteSnapshotTargets(t);}',
            't.done=true;WriteSnapshotTargets(t);RecordReplayTrade(t);}')
    helpers = '''bool RecordReplayQuote(MqlTick &q,int bar_index){
 replay_quote_index=replay_quotes_written;
 if(FileWriteLong(replay_quote_out,q.time_msc)!=8||FileWriteDouble(replay_quote_out,q.bid)!=8||FileWriteDouble(replay_quote_out,q.ask)!=8||FileWriteInteger(replay_quote_out,bar_index,INT_VALUE)!=4){Fatal("BAR REPLAY QUOTE WRITE FAILED");return false;}
 replay_quotes_written++;return true;
}
void RecordReplayTrade(VirtualTrade &t){
 if(replay_trades_written==0&&FileWriteString(replay_trade_out,"signal_id,virtual_mode,virtual_side,entry_quote_index,exit_quote_index,entry_time_msc,exit_time_msc,entry_price,exit_price,exit_reason,bars_in_trade\\r\\n")==0){snapshot_failed=true;return;}
 string line=t.signal_id+","+t.mode+","+(t.side==1?"BUY":"SELL")+","+IntegerToString(t.replay_entry_quote_index)+","+IntegerToString(replay_quote_index)+","+IntegerToString(t.entry_msc)+","+IntegerToString(t.exit_msc)+","+Num(t.entry)+","+Num(t.exit_price)+","+t.reason+","+IntegerToString(t.bars)+"\\r\\n";
 if(FileWriteString(replay_trade_out,line)==0){snapshot_failed=true;return;}replay_trades_written++;FileFlush(replay_trade_out);
}
'''
    replace('void CloseTrade(', helpers+'void CloseTrade(')
    replace(' execution_out=FileOpen(ExecutionQuoteOutputFile,',
            ' replay_quote_out=FileOpen(QuotePathOutputFile,FILE_WRITE|FILE_BIN);'
            'replay_trade_out=FileOpen(TradeIndexOutputFile,FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);'
            'if(replay_quote_out==INVALID_HANDLE||replay_trade_out==INVALID_HANDLE)return INIT_FAILED;\n'
            ' execution_out=FileOpen(ExecutionQuoteOutputFile,')
    replace(' if(stoch!=INVALID_HANDLE)IndicatorRelease(stoch);',
            ' if(replay_quote_out!=INVALID_HANDLE){FileFlush(replay_quote_out);FileClose(replay_quote_out);}'
            'if(replay_trade_out!=INVALID_HANDLE){FileFlush(replay_trade_out);FileClose(replay_trade_out);}\n'
            ' if(stoch!=INVALID_HANDLE)IndicatorRelease(stoch);')
    replace('\\"schema_version\\":\\"2.0\\"', '\\"schema_version\\":\\"3.0\\"')
    replace('\\"snapshot_schedule\\":\\"1,2,3,5,10,15,20,30,50\\"',
            '\\"snapshot_schedule\\":\\"' + schedule + '\\"')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Refusing to overwrite an existing derived producer')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding='utf-8', newline='\n')
    result = dict(status='PREPARED_NOT_DEPLOYED', schema_version='3.0',
                  base_sha256=hashlib.sha256(raw).hexdigest(), base_normalized_sha256=BASE_NORMALIZED_SHA256,
                  producer_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                  policy_class='M5_BAR_BOUNDARY_HOLD_EXIT_ONLY', FINAL_TEST='LOCKED', LIVE_TRADING=False,
                  execution_quotes='SEPARATE_FUTURE_EXECUTION_TABLE_NEVER_FEATURES',
                  quote_path_format='<qddi',quote_record_bytes=28,
                  execution_quote_role='DECISION_ARRIVAL_QUOTE_NOT_POLICY_FILL',
                  policy_fill='STRICTLY_AFTER_DECISION_ARRIVAL_SEQUENCE_WITH_PREDECLARED_LATENCY',
                  legacy_future_excursion_labels='NOT_ELIGIBLE_FOR_PROMOTION',
                  compile='NOT_RUN', causal_invariance='NOT_RUN', baseline_parity='NOT_RUN')
    destination.with_suffix('.manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


def build_probe(destination):
    """Derive the synthetic future-perturbation fixture for the prepared source."""
    source = (ROOT/'tests/mql5/SnapshotCausalProbe.mq5').read_text()
    old = '#include "..\\..\\Experts\\StochasticIntratradeResearch\\StochasticIntratradeResearchEA.mq5"'
    if source.count(old) != 1:
        raise ValueError('Causal fixture include changed')
    source = source.replace(old, '#include "StochasticBarDecisionResearchEA.mq5"')
    source = source.replace('failed=false;probe_failed=false;',
        'replay_quote_index=-1;replay_quotes_written=0;replay_trades_written=0;execution_rows=0;failed=false;probe_failed=false;')
    anchor = ' if(out==INVALID_HANDLE||snapshot_out==INVALID_HANDLE||target_out==INVALID_HANDLE)probe_failed=true;'
    if source.count(anchor) != 1:
        raise ValueError('Causal fixture output setup changed')
    source = source.replace(anchor,
        ' replay_quote_out=FileOpen(PROBE_ID+"_"+suffix+"_quote_path.bin",FILE_WRITE|FILE_BIN);\n'
        ' replay_trade_out=FileOpen(PROBE_ID+"_"+suffix+"_trade_index.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);\n'
        ' execution_out=FileOpen(PROBE_ID+"_"+suffix+"_execution_quotes.csv",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);\n'
        ' if(out==INVALID_HANDLE||snapshot_out==INVALID_HANDLE||target_out==INVALID_HANDLE||execution_out==INVALID_HANDLE||replay_quote_out==INVALID_HANDLE||replay_trade_out==INVALID_HANDLE)probe_failed=true;')
    anchor = 'FileClose(out);FileClose(snapshot_out);FileClose(target_out);'
    if source.count(anchor) != 1:
        raise ValueError('Causal fixture output teardown changed')
    source = source.replace(anchor, anchor+'FileFlush(execution_out);FileClose(execution_out);'
        'FileFlush(replay_quote_out);FileClose(replay_quote_out);FileFlush(replay_trade_out);FileClose(replay_trade_out);')
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError('Refusing to overwrite a causal fixture')
    destination.write_text(source, encoding='utf-8', newline='\n')
    return hashlib.sha256(destination.read_bytes()).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT/'mt5/StochasticIntratradeResearchEA.mq5', args.out), indent=2))
