#! /usr/bin/perl

$version = "1.1";

if ($ARGV[0] =~ /^-v$/) {
    print "subtractCooling.pl, version $version.\n";
    exit;
}
elsif ($ARGV[0] =~ /^-d(\d*)$/) {
    $debug =  $1 ? $1 : 1;
    print "Debug is $debug\n";
    shift @ARGV;
}

# autoflush STDOUT
$| = 1;

# Changed cooling punch to output rates, not fractions
$cloudyEdit = 1;

%metalComponentsOnly = ("cooling" => 1,
			"heating" => 1);

%{$omitComponents{cooling}} = ("CT C 0.0" => 1,
			       "hvFB 0.0" => 1);

$largeRunFile = shift @ARGV;
$smallRunFile = shift @ARGV;
$newRunFile = shift @ARGV;

$largeRunFile =~ /(\S+\/)/g;
$largeBaseDir = $1;
$smallRunFile =~ /(\S+\/)/g;
$smallBaseDir = $1;

$newRunFile =~ /(\S+\/)/g;
$newBaseDir = $1;
$newBaseDir .= "/" unless ($newBaseDir =~ /\/$/);
$newOutputPrefix = $newRunFile;
$newOutputPrefix =~ /$newBaseDir(.+)\./g;
$newOutputPrefix = $1;

mkdir $newBaseDir unless (-d $newBaseDir);

&getMapValues($largeRunFile,\@largeHeaderLines,\%largeRunStorage,\@largeLoopVars,\%largeLoopVarValues);
&getMapValues($smallRunFile,\@smallHeaderLines,\%smallRunStorage,\@smallLoopVars,\%smallLoopVarValues);

&assignMatches(\%largeRunStorage,\%smallRunStorage);
&createSubtractionGrid("cooling",\%largeRunStorage,\%smallRunStorage,\%subRunStorage);
&createSubtractionGrid("heating",\%largeRunStorage,\%smallRunStorage,\%subRunStorage);
&createSubtractionGrid("mmw",\%largeRunStorage,\%smallRunStorage,\%subRunStorage);

&writeSubtractionRunFile($newRunFile,\@largeHeaderLines);
&writeSubtractionGrid($newBaseDir,$newOutputPrefix,\%subRunStorage);

##########################################################################################################

sub writeSubtractionGrid {
    my ($dir,$prefix,$subRunPointer) = @_;

    my $filePrefix = sprintf "%s%s",$dir,$prefix;

    print "Writing grid.\n";

    my @subMaps = (sort {$a <=> $b} (keys %$subRunPointer));

    foreach $subMap (@subMaps) {
	&writeSubtractionMap($filePrefix,$subMap,$subRunPointer);
	&writeSubtractionComponentFile("cooling",$filePrefix,$subMap,$subRunPointer);
	&writeSubtractionComponentFile("heating",$filePrefix,$subMap,$subRunPointer);
    }
}

sub writeSubtractionComponentFile {
    my ($field,$filePrefix,$subMap,$subRunPointer) = @_;

    my $subComponentFile = sprintf "%s_run%d.%s",$filePrefix,$subMap,$field;

    open (OUT,">$subComponentFile");
    for (my $q = 0;$q < @{$$subRunPointer{$subMap}{data}{te}};$q++) {
	printf OUT "%.6e\t%.6e\t%.6e\t%.6e",0,$$subRunPointer{$subMap}{data}{te}[$q],
	$$subRunPointer{$subMap}{data}{heating}[$q],$$subRunPointer{$subMap}{data}{cooling}[$q];
	foreach $comp (keys %{$$subRunPointer{$subMap}{components}{$field}[$q]}) {
	    printf OUT "\t%s\t%.6e",$comp,$$subRunPointer{$subMap}{components}{$field}[$q]{$comp};
	}
	print OUT "\n";
    }
    close (OUT);
}

sub writeSubtractionMap {
    my ($filePrefix,$subMap,$subRunPointer) = @_;

    my $subMapFile = sprintf "%s_run%d.dat",$filePrefix,$subMap;
    my $hden = $$subRunPointer{$subMap}{loopVars}{hden};

    open (OUT,">$subMapFile");
    print OUT "# " . scalar (localtime) . "\n";
    print OUT "#\n";
    print OUT "# Subtracted Cooling Map\n";
    print OUT @{$$subRunPointer{$subMap}{header}};
    for (my $q = 0;$q < @{$$subRunPointer{$subMap}{data}{te}};$q++) {
	printf OUT "%.6e\t%.6e\t%.6e\t%.6f\n",
	$$subRunPointer{$subMap}{data}{te}[$q],
	$$subRunPointer{$subMap}{data}{heating}[$q]/(10**(2*$hden)),
	$$subRunPointer{$subMap}{data}{cooling}[$q]/(10**(2*$hden)),
	$$subRunPointer{$subMap}{data}{mmw}[$q];
    }
    close (OUT);
    
}

sub writeSubtractionRunFile {
    my ($file,$headerPtr) = @_;

    print "Writing run file.\n";

    open (OUT,">$file");
    foreach $line (@$headerPtr) {
	if ($line =~ /^\# Run started/) {
	    print OUT "# Subtraction started " . scalar (localtime) . "\n";
	    print OUT $line ."\n";
	}
	elsif ($line =~ /^\# outputFilePrefix/) {
	    print OUT "# outputFilePrefix = $newOutputPrefix\n";
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

sub createSubtractionGrid {
    my ($field,$largeRunPointer,$smallRunPointer,$subRunPointer) = @_;

    print "Performing subtraction: $field.\n";

    my @largeMaps = (sort {$a <=> $b} (keys %$largeRunPointer));
    my @largeKeys = keys %{$$largeRunPointer{$largeMaps[0]}{loopVars}};

    foreach $largeMap (@largeMaps) {
	%{$$subRunPointer{$largeMap}{loopVars}} = %{$$largeRunPointer{$largeMap}{loopVars}};
	@{$$subRunPointer{$largeMap}{header}} = @{$$largeRunPointer{$largeMap}{header}};

	@{$$subRunPointer{$largeMap}{data}{te}} = @{$$largeRunPointer{$largeMap}{data}{te}};

	my $smallOffset = 0;

      TE: for (my $q = 0;$q < @{$$largeRunPointer{$largeMap}{data}{te}};$q++) {
	  unless ($$largeRunPointer{$largeMap}{data}{te}[$q] == 
		  $$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{data}{te}[$q+$smallOffset]) {

	      my $foundSmall = 0;
	    OFFSET: for (my $w = 0;$w < @{$$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{data}{te}};$w++) {
		if ($$largeRunPointer{$largeMap}{data}{te}[$q] == $$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{data}{te}[$w]) {
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

	  if (defined($$largeRunPointer{$largeMap}{components}{$field})) {

	      printDebug(10,"Te: $$largeRunPointer{$largeMap}{data}{te}[$q]\n");

	      foreach $largeComponent (keys %{$$largeRunPointer{$largeMap}{components}{$field}[$q]}) {
		  my $tempKey = $largeComponent;
		  $tempKey =~ s/^\s+//;
		  $tempKey =~ s/\s+$//;

		  printDebug(10,"Comp: $largeComponent\n");
		  if (exists($$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{components}{$field}[$q+$smallOffset]{$largeComponent})) {
		      unless ($metalComponentsOnly{$field}) {
			  $$subRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent} = 
			      $$largeRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent} - 
			      $$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{components}{$field}[$q+$smallOffset]{$largeComponent};
			  printDebug(10,"\tLarge map: $$largeRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent} \t ");
			  printDebug(10,"Small map: $$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{components}{$field}[$q+$smallOffset]{$largeComponent}\n");
		      }
		  }
		  else {
		      unless ($omitComponents{$field}{$tempKey}) {
			  $$subRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent} = 
			      $$largeRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent};
			  printDebug(10,"\tLarge map: $$largeRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent}\n");
		      }
		  }
		  $$subRunPointer{$largeMap}{data}{$field}[$q] += $$subRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent}
		  if ($$subRunPointer{$largeMap}{components}{$field}[$q]{$largeComponent} > 0);
	      }
	  }
	  else {
	      printDebug(8,"No components for $field, performing simple subtraction.\n");
	      $$subRunPointer{$largeMap}{data}{$field}[$q] = $$largeRunPointer{$largeMap}{data}{$field}[$q] -
		  $$smallRunPointer{$$largeRunPointer{$largeMap}{match}}{data}{$field}[$q+$smallOffset];
	  }
	  printDebug(9,"Te: $$subRunPointer{$largeMap}{data}{te}[$q], $field: $$subRunPointer{$largeMap}{data}{$field}[$q]\n");

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
	die "No match found for map $largeMap.\n" 
	    unless (exists($$largeRunPointer{$largeMap}{match}));
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
	    my @header = ();
	    my @te = ();
	    my @heating = ();
	    my @cooling = ();
	    my @mmw = ();
	    my @coolingComponents = ();
	    my %theseAllCoolingComponents = ();
	    my %maxCoolingContribution = ();
	    my @heatingComponents = ();
	    my %theseAllHeatingComponents = ();
	    my %maxHeatingContribution = ();
	    my $coolingFile = $runBaseDir . $mapPrefix . "_run$run.cooling";
	    my $heatingFile = $runBaseDir . $mapPrefix . "_run$run.heating";
	    my $mapFile = $runBaseDir . $mapPrefix . "_run$run.dat";
	    &readComponentFile($coolingFile,\@te,\@heating,\@cooling,\@coolingComponents,\%theseAllCoolingComponents,\%maxCoolingContribution);
	    &readComponentFile($heatingFile,undef,undef,undef,\@heatingComponents,\%theseAllHeatingComponents,\%maxHeatingContribution);
	    &readMap($mapFile,\@header,undef,undef,undef,\@mmw);
	    @{$$storagePtr{$run}{header}} = @header;
	    @{$$storagePtr{$run}{data}{te}} = @te;
	    @{$$storagePtr{$run}{data}{heating}} = @heating;
	    @{$$storagePtr{$run}{data}{cooling}} = @cooling;
	    @{$$storagePtr{$run}{data}{mmw}} = @mmw;

	    foreach $component (keys %theseAllCoolingComponents) {
		$$allCoolingComponentPtr{$component} = 1;
	    }
	    foreach $component (keys %theseAllHeatingComponents) {
		$$allHeatingComponentPtr{$component} = 1;
	    }
	    print "After run $run, total components: " . scalar (keys %$allHeatingComponentPtr) . " heating and " . 
		scalar (keys %$allCoolingComponentPtr) . " cooling.\n";
	    @{$$storagePtr{$run}{components}{cooling}} = @coolingComponents;
	    %{$$storagePtr{$run}{maxContribution}{cooling}} = %maxCoolingContribution;
	    @{$$storagePtr{$run}{components}{heating}} = @heatingComponents;
	    %{$$storagePtr{$run}{maxContribution}{heating}} = %maxHeatingContribution;

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

sub readComponentFile {
    my ($mapFile,$tePtr,$heatingPtr,$coolingPtr,$componentPtr,$allComponentPtr,$maxContPtr) = @_;

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
	  if ($cloudyEdit) {
	      $theseComponents{$component} = $strength;
	  }
	  else {
	      $theseComponents{$component} = $strength * $$coolingPtr[-1];
	  }
	  $$maxContPtr{$component} = ($theseComponents{$component} > $$maxContPtr{$component}) ?
	      $theseComponents{$component} : $$maxContPtr{$component};
      }
      push @$componentPtr, \%theseComponents;

      foreach $component (keys %theseComponents) {
	  $$allComponentPtr{$component} = 1;
      }
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
