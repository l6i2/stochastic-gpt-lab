"""Own post-cut prefix native oracle in the EXISTING isolated terminal only.

No historical API queries, active-XM restart, orders, model fitting or admission.
Below 15 own M5 no terminal is launched. Monitor calls must be milestone-driven.
"""
import argparse,csv,json,shutil,subprocess,sys,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from controller.cf_feature_review import own_prefix,retained_oracle
from controller.authorized_capture import sha,once,manager_lock
from controller.native_diagnostic import BASE
from controller.prospective_processor import Processor,initial_state


def native_seed_diagnostic(bars, rows):
    """Compare an explanatory recurrence. The production feature remains untouched."""
    ranges = [bars[0]['high']-bars[0]['low']]
    ranges.extend(max(bar['high'],previous['close'])-min(bar['low'],previous['close'])
                  for previous,bar in zip(bars,bars[1:]))
    value = 0.0
    for span in ranges[:14]:
        value += span
    value /= 14
    mismatches = []
    direct_sum_mismatches = []
    seed_hex = value.hex()
    for index in range(13,len(bars)):
        if index>=14:
            value += (ranges[index]-ranges[index-14])/14
        native = float(rows[index]['atr'])
        if value!=native:
            mismatches.append(dict(index=index,computed_hex=value.hex(),native_hex=native.hex()))
        direct = sum(ranges[index-13:index+1])/14
        if direct!=native:
            direct_sum_mismatches.append(dict(index=index,computed_hex=direct.hex(),native_hex=native.hex()))
    return dict(compared=len(bars)-13,mismatches=mismatches,
                method='FIRST_BAR_HIGH_LOW_THEN_ORDERED_ROLLING_RECURRENCE',
                seed_hex=seed_hex,first_range_hex=ranges[0].hex(),
                direct_sum_mismatches=direct_sum_mismatches,
                arithmetic='BINARY64_ORDERED_SUM_THEN_ADD_DIFFERENCE_DIVIDED_BY_14',
                availability='CLOSED_PREFIX_ONLY_NO_FUTURE_BAR_USED',
                production_feature_modified=False)


def build_source(prefix,run):
    bars=prefix['native_m5'];minutes=prefix['native_m1'];n=len(bars)
    if n<15:raise ValueError('WAITING_FOR_15_OWN_M5')
    if len(minutes)!=n*5:raise ValueError('MISSING_OWN_M1')
    declarations=f' MqlRates bars[],minutes[];ArrayResize(bars,{n});ArrayResize(minutes,{n*5});\n'
    for name,rows in (('bars',bars),('minutes',minutes)):
        for i,row in enumerate(rows):
            declarations+=f' ZeroMemory({name}[{i}]);{name}[{i}].time=(datetime){int(row["time"])};'
            for field in ('open','high','low','close'):
                declarations+=f'{name}[{i}].{field}={float(row[field]):.17g};'
            declarations+=f'{name}[{i}].tick_volume={int(row["tick_volume"])};\n'
    text=(ROOT/'tests/mql5/ProspectiveIndicatorOracle.mq5').read_text()
    start=text.index(' MqlRates bars[],minutes[];');end=text.index(' if(CustomRatesUpdate',start)
    text=text[:start]+declarations+text[end:]
    text=text.replace('__RUN__',run).replace('!=2500',f'!={n*5}')
    text=text.replace('CopyBuffer(stoch,0,1,499,k)==499',f'CopyBuffer(stoch,0,0,{n},k)=={n}')
    text=text.replace('CopyBuffer(atr,0,1,499,a)==499',f'CopyBuffer(atr,0,0,{n},a)=={n}')
    text=text.replace('i<499',f'i<{n}').replace(',5,DoubleToString(k[i]',',bars[i].tick_volume,DoubleToString(k[i]')
    text=text.replace('"ha_direction","ha_ready"',
                      '"ha_direction","ha_ready","ha_open","ha_high","ha_low","ha_close"')
    text=text.replace('ha.Ready()?1:0);',
                      'ha.Ready()?1:0,DoubleToString(ha.bars[0].o,16),DoubleToString(ha.bars[0].h,16),DoubleToString(ha.bars[0].l,16),DoubleToString(ha.bars[0].c,16));')
    return text


def run():
    import psutil
    proof=retained_oracle(ROOT);prefix=own_prefix(ROOT);n=prefix['seeds']['own_bars']
    if n<15:return dict(status='WAITING_FOR_DATA',own_bars=n,required=15,native_terminal_launched=False)
    if psutil.virtual_memory().available<512*1024*1024:
        return dict(status='WAITING_FOR_RESOURCES',own_bars=n,native_terminal_launched=False,minimum_available_memory_bytes=512*1024*1024)
    # Existing isolated terminal lock and exact program hashes; never attach to active XM.
    with manager_lock(ROOT/'outputs/cf_own_indicator_oracle'):
        target=BASE/'terminal';programs=json.loads((BASE/'isolation_checkpoint.json').read_text())['program_hashes']
        for name,digest in programs.items():
            if sha(target/name)!=digest:raise ValueError('ISOLATED_PROGRAM_CHANGED')
        for process in psutil.process_iter(['exe']):
            if (process.info.get('exe') or '').lower()==str(target/'terminal64.exe').lower():raise ValueError('ISOLATED_TERMINAL_BUSY')
        original={p.pid for p in psutil.process_iter(['name']) if p.info['name']=='terminal64.exe'}
        nonce='cfown_'+uuid.uuid4().hex[:8];folder=ROOT/'outputs/cf_own_indicator_oracle'/nonce;folder.mkdir()
        scripts=target/'MQL5/Scripts/ProspectivePipeline'/nonce;scripts.mkdir(parents=True)
        source=scripts/'ProspectiveIndicatorOracle.mq5';source.write_text(build_source(prefix,nonce),encoding='utf8')
        shutil.copyfile(ROOT/'mt5/HeikinAshiCore.mqh',scripts/'HeikinAshiCore.mqh')
        once(folder/'input_manifest.json',dict(capture_id=prefix['capture_id'],epoch=prefix['epoch'],own_seed_bar_hash=prefix['seeds']['seed_bar_hash'],checkpoint=prefix['state_hash'],native_m5=len(prefix['native_m5']),native_m1=len(prefix['native_m1']),source_sha256=sha(source),retained_oracle=proof,origin='OWN_POST_CUT_OBSERVED_PREFIX_CLONED_ONLY_IN_ISOLATED_DIAGNOSTIC_SYMBOL',synthetic_bars_added=0))
        startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
        log=folder/'compile.log';editor=Path('C:/Program Files/XM Global SC MT5 Terminal/metaeditor64.exe')
        subprocess.run(f'"{editor}" /compile:"{source}" /log:"{log}"',startupinfo=startup,timeout=90)
        if '0 errors, 0 warnings' not in log.read_text(encoding='utf16') or not source.with_suffix('.ex5').exists():raise ValueError('OWN_ORACLE_COMPILE_FAILED')
        ini=folder/'own.ini';ini.write_text('[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n[StartUp]\nScript=ProspectivePipeline\\'+nonce+'\\ProspectiveIndicatorOracle\nSymbol=US30Cash\nPeriod=M5\nShutdownTerminal=1\n',encoding='utf16')
        process=subprocess.Popen(f'"{target/"terminal64.exe"}" /portable /config:"{ini}"',startupinfo=startup)
        try:process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            process.kill();process.wait(timeout=10)
            raise ValueError('OWN_ISOLATED_ORACLE_TIMEOUT_PRESERVED_NO_ACTIVE_XM_ACTION')
        output=target/'MQL5/Files'/(nonce+'_oracle.csv');shutil.copyfile(output,folder/output.name)
        with output.open(encoding='utf-8-sig') as stream:rows=list(csv.DictReader(stream))
        if len(rows)!=n:raise ValueError('OWN_ORACLE_INCOMPLETE')
        export_hash=sha(output)
        state=initial_state();emitted=[];clock=lambda:dict(boot_id='offline',monotonic_ns=0)
        processor=Processor(state,lambda kind,body:emitted.append(dict(kind=kind,**body)),None,'0.01',dict(warmup=350,signals=800,post_bars=100,evaluable=200,each_side=80),clock)
        checked=0;main_error=0;ha_mismatch=0;atr_mismatches=[]
        for native,bar in zip(rows,prefix['native_m5']):
            if int(native['time'])!=bar['time'] or any(float(native[k])!=bar[k] for k in ('open','high','low','close')) or int(native['volume'])!=bar['tick_volume']:raise ValueError('OWN_NATIVE_INPUT_CHANGED')
            state['own_run_bars']+=1
            processor.features(dict(bar,segment=prefix['epoch']),export_hash,dict(native_time_msc=(bar['time']+300)*1000),{})
            values=next(e for e in reversed(emitted) if e['kind']=='CAUSAL_PREFIX_FEATURES')['values']
            ha = state['ha']
            expected_ha = dict(ha_open=ha['open'], ha_close=ha['close'],
                               ha_high=max(bar['high'],ha['open'],ha['close']),
                               ha_low=min(bar['low'],ha['open'],ha['close']))
            if any(float(native[name])!=value for name,value in expected_ha.items()):
                ha_mismatch += 1
            if values['ATR'] is not None:
                checked+=1
                actual=float(native['atr'])
                if values['ATR']!=actual:
                    atr_mismatches.append(dict(index=checked+13,production_hex=values['ATR'].hex(),native_hex=actual.hex()))
            if values['stoch_k'] is not None:main_error=max(main_error,abs(values['stoch_k']-float(native['main_k'])))
            if int(native['ha_ready'])!=(values['ha_direction'] is not None) or values['ha_direction'] is not None and int(native['ha_direction'])!=values['ha_direction']:ha_mismatch+=1
        if main_error>1e-10 or ha_mismatch:raise ValueError('OWN_STOCH_OR_HA_PARITY_FAILED')
        result=dict(status='PASS_OWN_PREFIX_NATIVE_DIAGNOSTIC_ONLY',capture_id=prefix['capture_id'],epoch=prefix['epoch'],native_m5=n,ATR_compared=checked,ATR_PARITY='PASS_EXACT',HA_PARITY='PASS_EXACT' if n>=276 else 'SEED_BOUND_READY_VALUES_WAITING_276',MAIN_K_PARITY='PASS_RETAINED_BOUND',native_export_sha256=export_hash,input_manifest_sha256=sha(folder/'input_manifest.json'),source_sha256=sha(source),original_terminals_preserved=all(psutil.pid_exists(pid) for pid in original),orders_sent=0,training_executed=False,dataset_admitted=False)
        result['own_seed_bar_hash']=prefix['seeds']['seed_bar_hash']
        result['HA_OHLC_PARITY']='PASS_EXACT'
        result['HA_OHLC_compared']=n
        result['native_seed_diagnostic']=native_seed_diagnostic(prefix['native_m5'],rows)
        if atr_mismatches:
            result.update(status='FAILED_OWN_ATR_EXACT_PARITY',ATR_PARITY='FAIL_EXACT',
                          atr_mismatches=atr_mismatches)
        once(folder/'result.json',result);return dict(folder=str(folder),**result)


if __name__=='__main__':print(json.dumps(run(),indent=2))
