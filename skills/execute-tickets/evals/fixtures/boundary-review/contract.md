# Review replay

This excerpt is a decision fixture. It does not represent a deployed SDK.
Review the changed boundaries without editing them or inventing new requirements.

The SDK must preserve input text, including valid supplementary Unicode and
embedded NUL followed by text. Reference token counts and vectors come from an
independent invocation of the same model. Shape, normalization and positive usage
are also required. The current test below has no independent reference for its
edge input.

An accepted asynchronous request ends once with success or IPC_ERROR when the
transport reports a result-delivery failure and the error callback can still be
delivered. Complete transport loss is settled by the existing host disconnect
path. Host settlement already drops a duplicate late terminal result. Computing
or retransmitting vectors again is outside scope.

The production callback boundary can raise IPCException before delivering a
large successful response while a small error remains deliverable. Review this
specific failure; no physical buffer-exhaustion experiment is required.
