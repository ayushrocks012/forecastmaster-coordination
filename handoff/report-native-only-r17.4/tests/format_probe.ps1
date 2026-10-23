# Fabricated values only. Exercise Windows' numeric and date formatters.
$ErrorActionPreference='Stop'
$culture=[Globalization.CultureInfo]::InvariantCulture
$rows=@()
foreach($case in @(
 @{name='million';value=123456789.12;format='#,0,,.00"m"';expected='123.46m'},
 @{name='thousand';value=456789.12;format='#,0,.0"k"';expected='456.8k'},
 @{name='negative';value=-123456789.12;format='#,0,,.00"m"';expected='-123.46m'},
 @{name='true-zero';value=0;format='#,0.00';expected='0.00'},
 @{name='share';value=0.278;format='0.0%';expected='27.8%'})){
 $observed=([double]$case.value).ToString($case.format,$culture)
 if($observed -ne $case.expected){throw ('Format mismatch: '+$case.name+' '+$observed)}
 $rows+=@{Name=$case.name;Observed=$observed;Expected=$case.expected}
}
$date=New-Object datetime(2026,8,1)
$before=$date.ToString('mmm yyyy',$culture)
$after=$date.ToString('MMM yyyy',$culture)
if($before -notmatch '^0+ 2026$' -or $after -ne 'Aug 2026'){throw ('Month/minute regression mismatch: '+$before+' / '+$after)}
$rows+=@{Name='visual-month';Old=$before;Observed=$after;Expected='Aug 2026'}
@{Formatter='Windows .NET; comma placement also matches documented Power BI model syntax';Checks=$rows;DesktopRendering='NOT TESTED'}|ConvertTo-Json -Depth 8
