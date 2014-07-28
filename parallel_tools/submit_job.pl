#! /usr/bin/perl

$script = $ARGV[0];

$file = "job.dat";

$jobID = `qsub $script`;

open (OUT,">$file");
print OUT $jobID;
close (OUT);
