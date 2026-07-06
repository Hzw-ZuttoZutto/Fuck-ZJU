from __future__ import annotations

import sys

from src.cli.parser import build_parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "scan":
        from src.scan.service import run_scan

        return run_scan(args)
    if args.command == "analysis":
        from src.live.analysis import run_analysis

        return run_analysis(args)
    if args.command == "auto-analysis":
        from src.live.auto_analysis import run_auto_analysis

        return run_auto_analysis(args)
    if args.command == "tingwu-process":
        from src.live.tingwu import run_tingwu_process

        return run_tingwu_process(args)
    if args.command == "mic-listen":
        from src.live.mic import run_mic_listen

        return run_mic_listen(args)
    if args.command == "mic-publish":
        from src.live.mic import run_mic_publish

        return run_mic_publish(args)
    if args.command == "mic-list-devices":
        from src.live.mic import run_mic_list_devices

        return run_mic_list_devices(args)

    print(f"Unsupported command: {args.command}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
