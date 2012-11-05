#! /usr/bin/perl

$inputPartFile = shift @ARGV or die "Usage:
\t./combine_runfile_parts.pl <run part file (just one of them)>\n";

if ($inputPartFile =~ /\.part\d+\_(\d+)$/) {
    $totalParts = $1;
    $inputPartFile =~ s/\.part\d+\_\d+$//;
}
else {
    die "Improper run part file given.\n";
}

@header = ();
@runLines = ();

for (my $q = 1;$q <= $totalParts;$q++) {
    my $thisPartFile = sprintf "%s.part%d_%d",$inputPartFile,$q,$totalParts;

    open (IN,"<$thisPartFile") or die "Couldn't open $thisPartFile.\n";
    while (my $line = <IN>) {
	chomp $line;
	if ($line =~ /^\#/) {
	    push @header,$line if ($q == 1);
	}
	else {
	    push @runLines,$line;
	}
    }
    close (IN);

    print "Read $thisPartFile.\n";
}

print "Writing $inputPartFile.\n";
open (OUT,">$inputPartFile");
print OUT join "\n",@header;
print OUT "\n";
print OUT join "\n",@runLines;
print OUT "\n";
close (OUT);
