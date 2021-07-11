#!/bin/bash
suspend_stress_test --count 60000 --suspend_min 10 --suspend_max 15 --wake_min 10 --wake_max 15 --post_resume_command "cat /sys/kernel/debug/wakeup_sources" 2>&1 | tee /dev/tty | logger
