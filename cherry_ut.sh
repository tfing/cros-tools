#!/bin/bash
amixer -c0 cset name='O048 I070 Switch' 1
amixer -c0 cset name='O049 I071 Switch' 1
amixer -c0 cset name='ETDM_IN1_Clock_Source' a1sys_a2sys
