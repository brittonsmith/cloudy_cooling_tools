#! /usr/bin/perl

$debug = 0;

# autoflush STDOUT
$| = 1;

%metalComponentsOnly = ("cooling" => 1,
			"heating" => 1);

%{$omitComponents{cooling}} = ("CT C 0.0" => 1,
			       "hvFB 0.0" => 1);

$largeRunFile = shift @ARGV;
$smallRunFile = shift @ARGV;
$newRunFile = shift @ARGV;

unless (($largeRunFile) && ($smallRunFile) && ($newRunFile)) {
  die "Usage:
\t./subtract_cooling_lite.pl <run file 1> <run file 2> <new run file>
\tsuch that: (new run file) = (run file 1) - (run file 2).
"
}

$largeRunFile =~ /(\S+\/)/g;
$largePrefix = $largeRunFile;
$largePrefix =~ s/\.run$//;
$smallRunFile =~ /(\S+\/)/g;
$smallPrefix = $smallRunFile;
$smallPrefix =~ s/\.run$//;

$newRunFile =~ /(\S+\/)/g;
$newBaseDir = $1;
$newPrefix = $newRunFile;
$newPrefix =~ s/\.run$//;
$newShortPrefix = $newRunFile;
$newShortPrefix =~ /$newBaseDir(.+)\./g;
$newShortPrefix = $1;

mkdir $newBaseDir unless (-d $newBaseDir);

&getMapValues($largeRunFile,\@largeHeaderLines,\%largeRunStorage,\@largeLoopVars,\%largeLoopVarValues);
&getMapValues($smallRunFile,\@smallHeaderLines,\%smallRunStorage,\@smallLoopVars,\%smallLoopVarValues);

&createReverseLookup(\%smallRunStorage,\@smallLoopVars,\%lookupTable);

&writeRunFile(\@largeHeaderLines);
&subtract(\%largeRunStorage,\%smallRunStorage,\@smallLoopVars,\%lookupTable);

sub writeRunFile {
  my ($headerPtr) = @_;

  print "Writing run file: $newRunFile.\n";

  open (OUT,">$newRunFile");
  foreach $line (@$headerPtr) {
    if ($line =~ /^\# Run started/) {
      print OUT "# Subtraction started " . scalar (localtime) . "\n";
      print OUT $line ."\n";
    }
	elsif ($line =~ /^\# outputFilePrefix/) {
	  print OUT "# outputFilePrefix = $newShortPrefix\n";
	}
    elsif ($line =~ /^\# outputDir/) {
      print OUT "# outputDir = $newBaseDir\n";
    }
    else {
      print OUT $line . "\n";
    }
  }
  close (OUT);
}

sub subtract {
    my ($largeRunPtr,$smallRunPtr,$smallLoopVarsPtr,$lookupPtr) = @_;

    my @largeMaps = sort {$a <=> $b} (keys %$largeRunPtr);

    my $lookup;
    my $par;
    my $match;
    my $startTime = time;
    my $timeElapsed, $timeLeft, $speed;
    my $totalMaps = scalar @largeMaps;
    my $output;

    foreach $largeMap (@largeMaps) {
	$lookup = $lookupPtr;
	for (my $q = 0;$q < @$smallLoopVarsPtr;$q++) {
	    $par = $$largeRunPtr{$largeMap}{loopVars}{$$smallLoopVarsPtr[$q]};
	    if ($q < (@$smallLoopVarsPtr-1)) {
		$lookup = \%{$$lookup{$par}};
	    }
	    else {
		$match = $$lookup{$par};
	    }
	}
	$timeElapsed = time - $startTime;
	if ($timeElapsed > 0) {
	  $speed = $largeMap / $timeElapsed;
	  $timeLeft = ($totalMaps - $largeMap) / $speed;
	}
	else {
	  $timeLeft = -1;
	}
	print " " x length $output;
	print "\r";
	$output = sprintf "Subtracting maps: %d - %d. (Time remaining: %s, %.2f map/s)\r",
	  $largeMap,$match,timeConvert($timeLeft),$speed;
	print $output;
	&subtractMap($largeMap,$match);
    }
    print "\n";
}

sub timeConvert {
  my ($sec) = @_;

  if ($sec < 0) {
    return "--:--:--";
  }

  my $minutes = int($sec/60);
  my $seconds = $sec % 60;
  my $hours = int($minutes/60);
  $minutes = $minutes % 60;

  return sprintf "%02d:%02d:%02d",$hours,$minutes,$seconds;
}

sub subtractMap {
    my ($largeMap,$smallMap) = @_;

    my @largeTe,@largeHeating,@largeCooling,@largeMMW,@largeCoolingComponents,@largeHeatingComponents,@largeHeader;
    my @smallTe,@smallHeating,@smallCooling,@smallMMW,@smallCoolingComponents,@smallHeatingComponents,@smallHeader;
    my @subTe,@subHeating,@subCooling,@subMMW;
    my @largeHeatingUnscaled,@largeCoolingUnscaled;

    my $coolingFile = sprintf "%s_run%d.cooling", $largePrefix, $largeMap;
    my $heatingFile = sprintf "%s_run%d.heating", $largePrefix, $largeMap;
    my $mapFile = sprintf "%s_run%d.dat", $largePrefix, $largeMap;

    &readComponentFile($heatingFile,undef,\@largeHeatingUnscaled,undef,\@largeHeatingComponents);
    &readComponentFile($coolingFile,undef,undef,\@largeCoolingUnscaled,\@largeCoolingComponents);
    &readMap($mapFile,\@largeHeader,\@largeTe,\@largeHeating,\@largeCooling,\@largeMMW);

    $coolingFile = sprintf "%s_run%d.cooling", $smallPrefix, $smallMap;
    $heatingFile = sprintf "%s_run%d.heating", $smallPrefix, $smallMap;
    $mapFile = sprintf "%s_run%d.dat", $smallPrefix, $smallMap;

    &readComponentFile($heatingFile,undef,undef,undef,\@smallHeatingComponents);
    &readComponentFile($coolingFile,undef,undef,undef,\@smallCoolingComponents);
    &readMap($mapFile,\@smallHeader,\@smallTe,\@smallHeating,\@smallCooling,\@smallMMW);

    &subtractComponents('heating',\@largeHeating,\@largeHeatingUnscaled,\@largeHeatingComponents,\@smallHeatingComponents,\@largeTe,\@smallTe,\@subHeating);
    &subtractComponents('cooling',\@largeCooling,\@largeCoolingUnscaled,\@largeCoolingComponents,\@smallCoolingComponents,\@largeTe,\@smallTe,\@subCooling);
    &subtractValues('mmw',\@largeMMW,\@smallMMW,\@largeTe,\@smallTe,\@subMMW);

    &writeMap($largeMap,\@largeHeader,\@largeTe,\@subHeating,\@subCooling,\@subMMW);

    @largeTe = @largeHeating = @largeCooling = @largeMMW = @largeCoolingComponents = @largeHeatingComponents = @largeHeader = ();
    @smallTe = @smallHeating = @smallCooling = @smallMMW = @smallCoolingComponents = @smallHeatingComponents = @smallHeader = ();
    @subTe = @subHeating = @subCooling = @subMMW = ();
    @largeHeatingUnscaled = @largeCoolingUnscaled = ();
}

sub writeMap {
  my ($map,$headerPtr,$tePtr,$heatingPtr,$coolingPtr,$mmwPtr) = @_;

  my $mapFile = sprintf "%s_run%d.dat", $newPrefix, $map;

  printDebug(8,"Writing map: $mapFile.\n");

  open (OUT,">$mapFile");
  print OUT "# " . scalar (localtime) . "\n";
  print OUT "#\n";
  print OUT "# Subtracted Cooling Map\n";
  print OUT @$headerPtr;
  for (my $q = 0;$q < @$tePtr;$q++) {
    printf OUT "%.6e\t%.6e\t%.6e\t%.6f\n",$$tePtr[$q],$$heatingPtr[$q],$$coolingPtr[$q],$$mmwPtr[$q];
  }
  close (OUT);
}

sub subtractValues {
  my ($field,$largeValuePtr,$smallValuePtr,$largeTe,$smallTe,$subPointer) = @_;

    my $smallOffset = 0;

  TE: for (my $q = 0;$q < @{$largeTe};$q++) {
      unless ($$largeTe[$q] == $$smallTe[$q+$smallOffset]) {

	  my $foundSmall = 0;
	OFFSET: for (my $w = 0;$w < @{$smallTe};$w++) {
	    if ($$largeTe[$q] == $$smallTe[$w]) {
		$foundSmall = 1;
		$smallOffset = $w - $q;
		last OFFSET;
	    }
	}

	  if ($foundSmall) {
	      printDebug(9,"Switching offset for this map to $smallOffset.\n");
	  }
	  else {
	      next TE;
	  }

      }

      printDebug(10,"Te: $$largeTe[$q]\n");
      $$subPointer[$q] = $$largeValuePtr[$q] - $$smallValuePtr[$q];

      printDebug(10,"\tLarge value: $$largeValuePtr[$q]\t");
      printDebug(10,"\tSmall value: $$smallValuePtr[$q]\n");

      printDebug(9,"Te: $$largeTe[$q], $field: $$subPointer[$q]\n");

  }
  
}

sub subtractComponents {
    my ($field,$largeValuePtr,$largeValueUnscaledPtr,$largeCompPtr,$smallCompPtr,$largeTe,$smallTe,$subPointer) = @_;

    my $smallOffset = 0;
    my $subCompPtr;
    my $scalingFactor;

  TE: for (my $q = 0;$q < @{$largeTe};$q++) {
      unless ($$largeTe[$q] == $$smallTe[$q+$smallOffset]) {

	  my $foundSmall = 0;
	OFFSET: for (my $w = 0;$w < @{$smallTe};$w++) {
	    if ($$largeTe[$q] == $$smallTe[$w]) {
		$foundSmall = 1;
		$smallOffset = $w - $q;
		last OFFSET;
	    }
	}

	  if ($foundSmall) {
	      printDebug(9,"Switching offset for this map to $smallOffset.\n");
	  }
	  else {
	      next TE;
	  }

      }

      printDebug(10,"Te: $$largeTe[$q]\n");
      $scalingFactor = $$largeValuePtr[$q] / $$largeValueUnscaledPtr[$q];
      printDebug(10,sprintf "Scaling factor: %e.\n",$scalingFactor);
      $$subPointer[$q] = 0.0;

      foreach $largeComponent (keys %{$$largeCompPtr[$q]}) {
	  my $tempKey = $largeComponent;
	  $tempKey =~ s/^\s+//;
	  $tempKey =~ s/\s+$//;

	  printDebug(10,"Comp: $largeComponent\n");
	  if (exists($$smallCompPtr[$q+$smallOffset]{$largeComponent})) {
	    unless ($metalComponentsOnly{$field}) {
	      $$subCompPtr[$q]{$largeComponent} = $$largeCompPtr[$q]{$largeComponent} - 
		  $$smallCompPtr[$q+$smallOffset]{$largeComponent};
	      printDebug(10,"\tLarge map: $$largeCompPtr[$q]{$largeComponent} \t ");
	      printDebug(10,"Small map: $$smallCompPtr[$q+$smallOffset]{$largeComponent}\n");
	    }
	  }
	  else {
	      unless ($omitComponents{$field}{$tempKey}) {
		  $$subCompPtr[$q]{$largeComponent} = $$largeCompPtr[$q]{$largeComponent};
		  printDebug(10,"\tLarge map: $$largeCompPtr[$q]{$largeComponent}\n");
	      }
	  }
	  $$subPointer[$q] += $$subCompPtr[$q]{$largeComponent}
	  if ($$subCompPtr[$q]{$largeComponent} > 0);
      }

      $$subPointer[$q] *= $scalingFactor;
      printDebug(9,"Te: $$largeTe[$q], $field: $$subPointer[$q]\n");

  }
}

sub createReverseLookup {
    my ($storagePtr,$loopVarsPtr,$lookupPtr) = @_;

    %$lookupPtr = ();

    my @maps = (sort {$a <=> $b} (keys %$storagePtr));
    my $lookup;
    my $par;

    foreach $map (@maps) {
 	printf "Creating reverse lookup table: %d/%d.\r",$map,(scalar @maps);	
	$lookup = $lookupPtr;
 	for (my $q = 0;$q < @$loopVarsPtr;$q++) {
	    $par = $$storagePtr{$map}{loopVars}{$$loopVarsPtr[$q]};
	    if ($q < (@$loopVarsPtr - 1)) {
		unless ($$lookup{$par}) {
		    %{$$lookup{$par}} = ();
		}
		$lookup = \%{$$lookup{$par}};
	    }
 	    else {
 		$$lookup{$par} = $map;
 	    }
 	}
    }
    print "\n";
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

    open (IN, "<$runFile") or die "Couldn't open $runFile.\n";
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

sub assignMatches {
    my ($largeRunPointer,$smallRunPointer) = @_;

    print "Assigning matches.\n";

    my @matches = ();

    my @largeMaps = (sort {$a <=> $b} (keys %$largeRunPointer));
    my @smallMaps = (sort {$a <=> $b} (keys %$smallRunPointer));
    my @largeKeys = keys %{$$largeRunPointer{$largeMaps[0]}{loopVars}};
    my @smallKeys = keys %{$$smallRunPointer{$smallMaps[0]}{loopVars}};

    die "Small data set has more loop parameters than large data set.\n" 
	if (@smallKeys > @largeKeys);

    foreach $smallKey (@smallKeys) {
	die "Small data grid has loop parameter, $smallKey, and large data grid doesn't.\n"
	    unless (exists($$largeRunPointer{$largeMaps[0]}{loopVars}{$smallKey}));
    }

    foreach $largeMap (@largeMaps) {
      SEARCH: foreach $smallMap (@smallMaps) {
	  my $match = 0;
	  foreach $smallKey (@smallKeys) {
	      if ($$largeRunPointer{$largeMap}{loopVars}{$smallKey} == 
		  $$smallRunPointer{$smallMap}{loopVars}{$smallKey}) {
		  $match++;
	      }
	      else {
		  next SEARCH;
	      }
	  }
	  if ($match == scalar @smallKeys) {
	      $$largeRunPointer{$largeMap}{match} = $smallMap;
	      printDebug(1,"Large map $largeMap matches small map $smallMap.\n");
	      last SEARCH;
	  }
      }
	printf "Matching %d to %d.\r",$largeMap,$$largeRunPointer{$largeMap}{match};
	die "No match found for map $largeMap.\n" 
	    unless (exists($$largeRunPointer{$largeMap}{match}));
    }
}

sub readComponentFile {
    my ($mapFile,$tePtr,$heatingPtr,$coolingPtr,$componentPtr) = @_;

    my @lines = ();

    open (MAP,"<$mapFile") or die "Couldn't open $mapFile.\n";
    while (my $line  = <MAP>) {
	$line =~ s/^\s//;
	if ($line =~ /^\D/) {
	}
	else {
	    chomp $line;
	    push @lines, $line;
	}
    }
    close (MAP);

    # get only last iteration for each temperature
  LINE: for (my $q = 0;$q < @lines;$q++) {
      my @onLine = split /\t/, $lines[$q];
      if ($q < @lines - 1) {
	  my @onNextLine = split /\t/, $lines[$q+1];
	  if ($onLine[1] == $onNextLine[1]) {
	      next LINE;
	  }
      }
      shift @onLine;
      push @$tePtr, shift @onLine;
      push @$heatingPtr, shift @onLine;
      push @$coolingPtr, shift @onLine;

      my %theseComponents = ();

      while (my $component = shift @onLine) {
	  my $strength = shift @onLine;
	  $theseComponents{$component} = $strength;
      }
      push @$componentPtr, \%theseComponents;

  }
}

sub readMap {
    my ($mapFile,$headerPtr,$tePtr,$heatingPtr,$coolingPtr,$mmwPtr) = @_;

    open (MAP,"<$mapFile") or die "Couldn't open $mapFile.\n";
    while (my $line  = <MAP>) {
	if ($line =~ /^\#/) {
	    push @$headerPtr,$line;
	}
	else {
	    chomp $line;
	    my @onLine = split /\t/,$line;
	    push @$tePtr, $onLine[0];
	    push @$heatingPtr, $onLine[1];
	    push @$coolingPtr, $onLine[2];
	    push @$mmwPtr, $onLine[3];
	}
    }
    close (MAP);
}

sub printDebug {
    my ($level,$string) = @_;

    print $string if ($debug >= $level);
}
