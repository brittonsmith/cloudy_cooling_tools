#! /usr/bin/perl

$jobFile = "job.dat";
$machineFile = "machines.dat";

open (IN, "<$jobFile") or die "No job file.\n";
$jobID = <IN>;
close (IN);

$jobID =~ /^(\d+)\./;
$jobID = $1;

@nodes = getJobNodes($jobID);

open (OUT,">$machineFile");
foreach $node (@nodes) {
    if ($node =~ /:ppn=(\d+)/) {
	my $ppn = $1;
	$node =~ s/:.+//;
	for (my $q = 0;$q < $ppn;$q++) {
	    print OUT "$node:1\n";
	}
    }
    else {
	print OUT "$node:1\n";
    }
}
close (OUT);

sub getJobNodes {
    my ($jobID) = @_;
    my @nodes;
    my @jobInfoLines = split /\n/,`qstat -n -1 $jobID`;
    my $jobLine = substr $jobInfoLines[-1],87;
    $jobLine =~ s/\s//g;
    $jobLine =~ s/\/\d*\+/\+/g;
    $jobLine =~ s/\/\d*$//;
    @nodes = split /\+/,$jobLine;
    return @nodes;
}
