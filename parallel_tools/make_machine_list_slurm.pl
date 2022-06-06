#! /usr/bin/perl

$machineFile = "machines.dat";

@nodes = getJobNodes($ENV{'SLURM_NODELIST'});
$ppn = $ENV{'SLURM_NTASKS_PER_NODE'};

open (OUT,">$machineFile");
foreach $node (@nodes) {
    for (my $q = 0;$q < $ppn;$q++) { # print the node ppn times
        print OUT "$node:1\n";
    }
}
close (OUT);

sub getJobNodes {
    my ($nodeList) = @_;
    my @nodes;

    while ($nodeList =~ /([\w-]+)\[([\d,-]+)\]/g) {
        $nodeName = $1;
        $nodeNumList = $2;
        my @nodeNums = split /,/, $nodeNumList;

        foreach $num (@nodeNums) {
            if ($num =~ m/(\d+)-(\d+)/) {
                for ($1..$2) { # preserves any leading 0's
                    push @nodes, $nodeName.$_;
                }
            } else {
                push @nodes, $nodeName.$num;
            }
        }
    }

    return @nodes;
}
