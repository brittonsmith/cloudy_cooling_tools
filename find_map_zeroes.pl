#! /usr/bin/perl

$version = "1.0";

if ($ARGV[0] =~ /^-v$/) {
    print "$0, version $version.\n";
    exit;
}
elsif ($ARGV[0] =~ /^-d(\d*)$/) {
    $debug =  $1 ? $1 : 1;
    print "Debug is $debug\n";
    shift @ARGV;
}

if (@ARGV < 4) {
    die "Usage: $0 <T_lower> <T_upper> <num T points> <run file>\n";
}

# autoflush STDOUT
$| = 1;

# log steps or linear
$logSteps = 1;
$tempPrecision = 6;
$dataPrecision = 6;

$Tlower = shift @ARGV;
$Tupper = shift @ARGV;
$Tsteps = shift @ARGV;
$largeRunFile = shift @ARGV;

$largeRunFile =~ /(\S+\/)/g;
$largeBaseDir = $1;
$largeRunPrefix = $largeRunFile;
$largeRunPrefix =~ s/$largeBaseDir//;
$largeRunPrefix =~ s/\.run//;

&makeTemperatureList();
&getMapValues($largeRunFile,\@largeHeaderLines,\%largeRunStorage,\@largeLoopVars,\%largeLoopVarValues);
&writeFixList();

##########################################################################################################

sub writeFixList {
    if (@zeroFiles) {
	print "Writing fix list with " . scalar @zeroFiles . " maps.\n";

	my $fixFile = $largeRunPrefix . ".fix";
	open (FIX,">$fixFile");
	print FIX join "\n",@zeroFiles;
	print FIX "\n";
	close (FIX);
    }
    else {
	print "This run is complete.\n";
    }
}

sub makeTemperatureList {
    my $temp = $Tlower;
    my $step;

    print "Creating temperature list.\n";

    if ($logSteps) {
	$step = log($Tupper/$Tlower)/log(10)/($Tsteps-1);
    }
    else {
	$step = ($Tupper-$Tlower)/($Tsteps-1);
    }

    while ($temp <= $Tupper) {
	push @temperature, sprintf "%.".$tempPrecision."e",$temp;

	if ($logSteps) {
	    my $logTemp = log($temp)/log(10);
	    $temp = 10**($logTemp+$step);
	}
	else {
	    $temp += $step;
	}
    }
}

sub findZeroes {
    my ($mapFile) = @_;

    printDebug(1,"Looking for zeros in $mapFile.\n");

    my $hasZero = 0;

    my @header;
    my @te = ();
    my @heating = ();
    my @cooling = ();
    my @mmw = ();
    my $tindex = 0;

    open (MAP,"<$mapFile") or die "Couldn't open $mapFile.\n";
    while (my $line  = <MAP>) {
	if ($line =~ /^\#/) {
	    push @header,$line;
	}
	else {
	    chomp $line;
	    my @onLine = split /\t/,$line;
	    while ($temperature[$tindex] != $onLine[0]) {
		$hasZero++;
		printDebug(1,"Adding T = $temperature[$tindex] to $mapFile.\n");
		push @te,$temperature[$tindex];
 		push @heating, sprintf "%.".$dataPrecision."e",0;
 		push @cooling, sprintf "%.".$dataPrecision."e",0;
 		push @mmw, sprintf "%.".$dataPrecision."f",0;;
		$tindex++;
	    }
	    push @te, $onLine[0];
	    push @heating, $onLine[1];
	    push @cooling, $onLine[2];
	    push @mmw, $onLine[3];
	    $tindex++;
	}
    }
    close (MAP);

    if ($hasZero) {
	$mapFile =~ /_run(\d+)\.dat/;
	my $run = $1;
	push @zeroFiles, $run;

	print "Adding $hasZero zeroes to $run\n";

	my $newFile = $mapFile . ".new";
	open (OUT,">$newFile");
	print OUT @header;
	for (my $q = 0;$q < @te;$q++) {
	    print OUT "$te[$q]\t$heating[$q]\t$cooling[$q]\t$mmw[$q]\n";
	}
	close (OUT);

	system("mv $newFile $mapFile");
    }
}

sub getMapValues {
    my ($runFile,$headerLinesPtr,$storagePtr,$loopVarsPtr,$loopVarValuesPtr) = @_;

    my $allCoolingComponentPtr,$allHeatingComponentPtr;

    print "Loading grid data: $runFile\n";

    $runFile =~ /(\S+\/)/g;
    my $runBaseDir = $1;

    my @otherLines = ();
    my $mapDir;
    my $mapPrefix;

    open (IN, "<$runFile") or die "Coudln't open $runFile.\n";
    while (my $line = <IN>) {
	chomp $line;
	if ($line =~ /^\#run/) {
	    (undef,@{$loopVarsPtr}) = split /\t/,$line;
	    push @$headerLinesPtr,$line;
	}
	elsif ($line =~ /^\# outputFilePrefix/) {
	    (undef,$mapPrefix) = split / = /,$line;
	    push @$headerLinesPtr,$line;
	}
	elsif ($line =~ /^\# outputDir/) {
	    (undef,$mapDir) = split / = /,$line;
	    push @$headerLinesPtr,$line;
	}
	elsif ($line != /^\#/) {
	    push @$headerLinesPtr,$line;
	    my @lineStuff = split /\t/,$line;
	    my $run = $lineStuff[0];
	    for (my $q = 1;$q < @lineStuff;$q++) {
		$$storagePtr{$run}{loopVars}{$$loopVarsPtr[$q-1]} = $lineStuff[$q];
	    }
	    my $mapFile = $runBaseDir . $mapPrefix . "_run$run.dat";
	    &findZeroes($mapFile);
	}
	else {
	    push @otherLines,$line;
	    push @$headerLinesPtr,$line;
	}
    }
    close (IN);

    my %checkVars;
    foreach $loopVar (@{$loopVarsPtr}) {
	$checkVars{$loopVar} = 1;
    }
    foreach $otherLine (@otherLines) {
      CHECK: foreach $loopVar (@{$loopVarsPtr}) {
	  if ($checkVars{$loopVar}) {
	      my $copy = $loopVar;
	      $copy =~ s/(\W)/\\$1/g; # it wasn't matching vars like "metals * log"
	      if ($otherLine =~ /^\# $copy\:/) {
		  $otherLine =~ s/^\# $copy\: //;
		  @{$$loopVarValuesPtr{$loopVar}} = split " ",$otherLine;
		  $checkVars{$loopVar} = 0;
		  last CHECK;
	      }
	  }
      }
    }
}

sub printDebug {
    my ($level,$string) = @_;

    print $string if ($debug >= $level);
}
