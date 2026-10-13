"""Create bounded, non-optimizing MT5 tester configs that stop before FINAL_TEST."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from .parquet_io import read_parquet
except ImportError:
    from parquet_io import read_parquet

ROOT = Path(__file__).resolve().parents[1]


def create_plan(output: Path, validation_path: Path, expert: str =
                "StochasticResearch\\StochasticIntratradeResearchEA.ex5") -> dict:
    split = json.loads((ROOT / "outputs/splits/split_manifest.json").read_text(encoding="utf-8"))
    final_start_msc = int(split["boundaries"]["final_test_start_signal_time_msc"])
    validation = read_parquet(validation_path)
    last_validation_msc = int(validation["signal_time_msc"].max())
    last_validation_day = datetime.fromtimestamp(last_validation_msc / 1000, timezone.utc).date()
    final_day = datetime.fromtimestamp(final_start_msc / 1000, timezone.utc).date()
    if last_validation_day >= final_day:
        raise ValueError("Cannot safely map the validation boundary to a tester day; export blocked")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    last_day = last_validation_day.strftime("%Y.%m.%d")
    blocks = [
        ("2023_12", "2023.12.20", "2023.12.31"),
        ("2024", "2024.01.01", "2024.12.31"),
        ("2025", "2025.01.01", "2025.12.31"),
        ("2026_validation_only", "2026.01.01", last_day),
    ]
    output.mkdir(parents=True, exist_ok=True)
    configs = []
    for period, start, end in blocks:
        if period.startswith("2026") and end >= final_day.strftime("%Y.%m.%d"):
            raise ValueError("Generated 2026 export period could include FINAL_TEST")
        stem = f"intratrade_{period}_{run_id}"
        preset = stem + ".set"
        settings = [
            "LIVE_TRADING=false||false||0||true||N", "ResearchSymbol=",
            "trigger_line=0||0||0||1||N", "simulation_mode=0||0||0||1||N",
            "ConfirmRealTickTesterMode=true||false||0||true||N", "profile_weight=0||0||0||1||N",
            "ProfileBinSize=10.0||10.0||1.000000||100.000000||N",
            "ProfileMaxBins=20000||20000||1||200000||N", "SessionStartServerHour=0||0||1||10||N",
            "ServerUTCOffsetWinterHours=2||2||1||20||N", "ServerDSTRule=1||0||0||2||N",
            f"OutputFile=events_{period}_{run_id}.csv",
            f"SnapshotOutputFile=intratrade_snapshots_{period}_{run_id}.csv",
            f"TargetOutputFile=intratrade_targets_{period}_{run_id}.csv",
        ]
        (output / preset).write_text("\n".join(settings) + "\n", encoding="ascii")
        ini = ["[Charts]", "MaxBars=1000000", "[Experts]", "AllowLiveTrading=0", "[Tester]",
               f"Expert={expert}", f"ExpertParameters={preset}", "Symbol=US30Cash", "Period=M5",
               "Model=4", "Optimization=0", f"FromDate={start}", f"ToDate={end}",
               "ForwardMode=0", "Deposit=10000", "Currency=USD", "Leverage=100",
               "ExecutionMode=0", "UseLocal=1", "UseRemote=0", "UseCloud=0",
               "Visual=0", "ShutdownTerminal=1"]
        ini_path = output / (stem + ".ini")
        ini_path.write_text("\n".join(ini) + "\n", encoding="ascii")
        configs.append({"period": period, "from": start, "to": end,
                        "ini": str(ini_path.relative_to(ROOT)), "preset": str((output / preset).relative_to(ROOT)),
                        "final_test_accessed": False})
    result = {"status": "CONFIGS_READY_MANUAL_MT5_START_REQUIRED", "run_id": run_id,
              "symbol": "US30Cash", "timeframe": "M5", "model": "Every tick based on real ticks",
              "optimization": "OFF", "LIVE_TRADING": False,
              "final_test_start_msc": final_start_msc,
              "last_validation_signal_msc": last_validation_msc,
              "last_validation_export_day": last_day, "final_test_accessed": False,
              "terminal_launch_automated": False, "blocks": configs}
    (output / "plan.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("outputs/verification/intratrade_export_plan"))
    parser.add_argument("--validation", type=Path, default=Path("outputs/splits/validation.parquet"))
    args = parser.parse_args()
    out = args.output if args.output.is_absolute() else ROOT / args.output
    validation = args.validation if args.validation.is_absolute() else ROOT / args.validation
    try:
        result = create_plan(out, validation)
    except (OSError, ValueError, KeyError) as exc:
        print(f"INTRATRADE EXPORT PLAN BLOCKED: {exc}")
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
