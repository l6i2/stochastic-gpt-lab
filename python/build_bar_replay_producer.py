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
                  legacy_future_excursion_labels='NOT_ELIGIBLE_FOR_PROMOTION',
                  compile='NOT_RUN', causal_invariance='NOT_RUN', baseline_parity='NOT_RUN')
    destination.with_suffix('.manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(ROOT/'mt5/StochasticIntratradeResearchEA.mq5', args.out), indent=2))
