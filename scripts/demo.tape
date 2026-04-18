# vhs tape for the README demo GIF.
#
# Rendered with charmbracelet/vhs:
#   brew install vhs
#   vhs scripts/demo.tape         # from the repo root
#   vhs demo.tape                 # from inside scripts/
#
# The recording runs scripts/demo-session.sh, which self-locates and
# prints a scripted before/after session with sleeps. Deterministic —
# no LLM call, works in CI.

Output assets/demo.gif

Set Shell "bash"
Set FontSize 13
Set Width  1100
Set Height 620
Set Theme "Dracula"
Set TypingSpeed 40ms
Set Padding 18

# Silent setup — clear screen and kick off the scripted session without
# showing the shell prompt or the bash invocation itself.
Hide
Type "clear"
Enter
Type "bash scripts/demo-session.sh 2>/dev/null || bash ./demo-session.sh"
Enter
Sleep 200ms
Show

# Let the scripted session play out. demo-session.sh's internal sleeps
# total around 7 seconds — give it some headroom.
Sleep 8s

# Trailing blank frame so the final numbers linger.
Sleep 1200ms
