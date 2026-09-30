# Nebius × NVIDIA Hackathon Build Plan

## Track

Primary target: **Best Apps and Agents**.

FlowBound is a multi-step autonomous inspection workflow rather than a coding agent. The competition build uses NVIDIA Nemotron through Nebius Token Factory for interpretation and action proposals while keeping consequential state changes behind deterministic authority gates.

## Competition-period changes

The pre-existing FlowBound project is being significantly updated during the submission period with:

1. a three-stage Nebius Token Factory / NVIDIA Nemotron fleet;
2. explicit Nebius provider/model/trace provenance in transition records;
3. runtime configuration for Token Factory;
4. a stronger adversarial demonstration showing pre-model quarantine and post-model authority enforcement;
5. submission-specific runtime evidence and demo material.

## Runtime path

```
field evidence
   |
pre-model trust boundary
   |
Nemotron intake
   |
Nemotron evidence challenge
   |
Nemotron bounded action proposal
   |
FlowBound deterministic policy + authority gate
   |
compare-and-set execution
   |
successor re-observation
   |
accept OR recovery block
```

Default inference endpoint:

`https://api.tokenfactory.nebius.com/v1/`

Default NVIDIA model:

`nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`

Optional evidence-challenge model:

`nvidia/nemotron-3-super-120b-a12b`

## Security boundary

The Token Factory API key is read only from environment variables and is never stored in the repository. The model receives evidence and state context but does not receive authority to execute, choose successor state, or mark its own work successful.

## Frequency gate: licensing

The hackathon rules require the submitted repository to be public **and open source** under a license such as Apache-2.0, MIT, or MPL-2.0.

The existing FlowBound repository is PolyForm Noncommercial and is therefore **not submission-compatible as-is**. This branch deliberately does not change that license.

Before submission, create a separate competition repository containing only the self-contained competition implementation and explicitly license that repository under an approved open-source license, or make a deliberate relicensing decision. Do not silently convert the main FlowBound product license.

## Runtime proof still required

Before submission we still need:

- a real Nebius Token Factory API key;
- a successful `/v1/models` authentication check;
- at least one successful live Nemotron workflow;
- a hosted working demo URL;
- a public <=3 minute YouTube demo;
- explicit written feedback on Nebius/NVIDIA tooling;
- a public open-source competition repository.
