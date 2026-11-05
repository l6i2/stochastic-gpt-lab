import unittest,subprocess,tempfile,os
from pathlib import Path

class StationRecoveryPolicyTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows recovery policy')
    def test_headless_recovery_requires_all_independent_safety_conditions(self):
        source=Path(__file__).resolve().parents[1]/'tools/research_recovery.ps1'
        command="""$errors=$null;$tokens=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile('SOURCE',[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'PARSE_FAILED'}
$fn=$ast.Find({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Test-HeadlessCaptureStall'},$true)
Invoke-Expression $fn.Extent.Text
if(!(Test-HeadlessCaptureStall ([IntPtr]::Zero) 300 300000 1)){throw 'POSITIVE_CASE_FAILED'}
if(Test-HeadlessCaptureStall 123 900 900000 1){throw 'VISIBLE_TERMINAL'}
if(Test-HeadlessCaptureStall 0 299 900000 1){throw 'STARTUP_GRACE'}
if(Test-HeadlessCaptureStall 0 900 299999 1){throw 'RECENT_CALLBACK'}
if(Test-HeadlessCaptureStall 0 900 900000 121){throw 'STALE_STATUS'}
if(Test-HeadlessCaptureStall 0 900 900000 -1){throw 'FUTURE_STATUS'}
'PASS'
""".replace('SOURCE',str(source).replace("'","''"))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'synthetic_policy.ps1';p.write_text(command,encoding='utf8')
            result=subprocess.run(['powershell.exe','-NoProfile','-File',str(p)],capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('PASS',result.stdout)

if __name__=='__main__':unittest.main()
