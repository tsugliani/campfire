---
title: The Limits of NTP Accuracy on Linux
url_link: https://scottstuff.net/posts/2025/05/19/ntp-limits/
tags:
- linux
- networking
- time
- accuracy
description: 'Lately I’ve been trying to find (and understand) the limits of time
  syncing between Linux systems. How accurate can you get? What does it take to get
  that? And what things can easily add measurable amounts of time error?

  After most of a month (!), I’m starting to understand things. This is kind of a
  follow-on to a previous post, where I walked through my setup and goals, plus another
  post where I discussed time syncing in general. I’m trying to get the clocks on
  a bunch of Linux systems on my network synced as closely as possible so I can trust
  the timestamps on distributed tracing records that occur on different systems. My
  local network round-trip times are in the 20–30 microsecond (μs) range and I’d like
  clocks to be less than 1 RTT apart from each other. Ideally, they’d be within 1
  μs, but 10 μs is fine.

  It’s easy to fire up Chrony against a local GPSTechnically, GNSS, which covers multiple
  satellite-backed navigation systems, not just the US GPS system, but I’m going to
  keep saying “GPS” for short.

  -backed time source and see it claim to be within X nanoseconds of GPS, but it’s
  tricky to figure out if Chrony is right or not. Especially once it’s claiming to
  be more accurate than the network’s round-trip time20 μs or so.

  , the amount of time needed for a single CPU cache miss50-ish nanoseconds.

  , or even the amount of time that light would take to span the gap between the server
  and the time source.About 5 ns per meter.

  I’ve spent way too much time over the past month digging into time, and specifically
  the limits of what you can accomplish with Linux, Chrony, and GPS. I’ll walk through
  all of that here eventually, but let me spoil the conclusion and give some limits:

  GPSes don’t return perfect time. I routinely see up to 200 ns differences between
  the 3 GPSes on my desk when viewing their output on an oscilloscope. The time gap
  between the 3 sources varies every second, and it’s rare to see all three within
  20 ns of each other. Even the best GPS timing modules that I’ve seen list ~5 ns
  of jitter on their datasheets. I’d be surprised if you could get 3-5 GPS receivers
  to agree within 50 ns or so without careful management of consistent antenna cable
  length, etc. Even small amounts of network complexity can easily add 200-300 ns
  of systemic error to your measurements. Different NICs and their drivers vary widely
  on how good they are for sub-microsecond timing. From what I’ve seen, Intel E810
  NICs are great, Intel X710s are very good, Mellanox ConnectX-5 are okay, Mellanox
  ConnectX-3 and ConnectX-4 are borderline, and everything from Realtek is questionable.
  A lot of Linux systems are terrible at low-latency work. There are a lot of causes
  for this, but one of the biggest is random “stalls” due to the system’s SMBIOS running
  to handle power management or other activities, and “pausing” the observable computer
  for hundreds of microseconds or longer. In general, there’s no good way to know
  if a given system (especially cheap systems) will be good or bad for timing without
  testing them. I have two cheap mini PC systems that have inexplicably bad time syncing
  behavior,1300-2000 ns.

  and two others with inexplicably good time syncing20-50 ns

  . Dedicated server hardware is generally more consistent. All in all, I’m able to
  sync clocks to within 500 ns or so on the bulk of the systems on my network. That’s
  good enough for my purposes, but it’s not as good as I’d expected to see.'
date: '2025-05-19'
year: 2025
week: 21
comments: []
---
