# Logging and sensor reliability

On PS5, llama.cpp's asynchronous log writer prints to stdout and the configured
log file. If either sink stalls, the 512-entry queue can fill and block a server
thread trying to log. `/health` can still answer while `/slots`, `/metrics`, or an
inference request waits. A healthy `/health` alone is not a readiness test.

`patches/0006-log-never-blocks.patch` backports the PS5-only queue policy from
[cobanov/PS5LM v0.9.1](https://github.com/cobanov/PS5LM/blob/88063d23500e7ea90d6a83a7156e556dc2d62b7a/patches/0008-log-never-blocks.patch)
(by @bilawalriaz). Text and JSON producers drop new entries when the queue is full;
the writer reports the number dropped once it catches up. Other platforms retain
their blocking behavior. Logs may be incomplete under backpressure. Explicit
flush/shutdown can still wait for a stalled sink; this change protects producers,
not every logging operation.

The app also bundles ps5-exporter v0.3.1, pinned by SHA-256 in `build-app.sh`.
This updates sensor reporting; it does not change the fan policy.

## Validation

After applying the patches to the pinned llama.cpp submodule, run:

```sh
python3 scripts/test-log-backpressure.py
```

This host-side regression test blocks a real pipe used as stderr and exercises
text and JSON logging under both the PS5 queue policy and the native policy.
It does not emulate the console or replace a complete application build and hardware test.
The same logger test can also be compiled as a PS5 payload:

```sh
PS5_PAYLOAD_SDK=/absolute/path/to/ps5-payload-sdk bash scripts/build-log-test-ps5.sh
```

The build script never launches it. When explicitly run through elfldr, it tests
text and JSON logging and writes `/data/PS5LM/log-backpressure-test.jsonl`.
It refuses to overwrite an existing result; archive that file before another run.
A 20-second watchdog exits the test payload if the logger fails to recover.
The payload neither loads a model nor changes the running application or fan.
The PR was checked with official payload SDK v0.45 and LLVM 23.1.4.
On-console text and JSON cases completed with exit code 0; Plus remained healthy.
This validates the logger component on PS5, not a rebuilt graphical application.

The `Log reliability` GitHub Actions workflow repeats the host test on Linux and
macOS and cross-compiles the PS5 test using a hash-verified SDK.

For console validation, use one client, check `/slots` is idle before starting,
and record request success, generation throughput, `/health`, `/slots`, and
independent sensor telemetry. Compare identical prompts over time; different
prompt lengths naturally change throughput. Include streaming, tool calls,
and contexts near the configured capacity, with room for output tokens.

An external investigation of the published v0.8.4 build observed 86 successful
requests and no inference failures across about 53 minutes with logging disabled
and a 75 C automatic fan target, including a 30-minute mixed-prompt run (48
requests, mean 53.70 generated tokens/s). This is evidence for that combined
workaround, not hardware validation of this source patch or proof of a thermal
or logging root cause. Transient monitoring connection errors remained.

For existing releases, `--log-disable` in `/data/PS5LM/app-args.txt` can suppress
llama logging, but that file overrides the entire planner argument list, and
model selection can remove it. Preserve a backup and recheck after model changes.
A source build containing the queue patch does not depend on this override.
Fan targets are console preferences: the project does not impose a target.
