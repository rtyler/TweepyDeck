#!/bin/sh

xgettext -k_ -kN_ -o messages.pot TweepyDeck/*.py
msgmerge -U de.po messages.pot
msgfmt de.po -o locale/de/LC_MESSAGES/tweepydeck.mo
