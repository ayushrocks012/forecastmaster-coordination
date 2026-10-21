"""Report-specific projection contract; raw V18 observations remain the authority."""

PREFIX = "fm_review"
MEASURES = PREFIX + "_measures"
FILES = PREFIX + "_files"
REFERENCE = PREFIX + "_reference"
FACTS = PREFIX + "_facts"
MONTHS = PREFIX + "_months"
AXIS = PREFIX + "_axis"
PERIODS = PREFIX + "_periods"
SERIES = PREFIX + "_series"
MODES = PREFIX + "_modes"

TABLES = {
    FILES: {"SourceRevisionID":"string", "FileLabel":"string", "SourceFileName":"string", "SourceRelativePath":"string", "Country":"string", "DemandCycle":"string", "GrowthDriver":"string", "SourceProfile":"string", "IMSActualsThrough":"dateTime", "ExFactoryActualsThrough":"dateTime", "PublicationStatus":"string"},
    FACTS: {"SourceRevisionID":"string", "Channel":"string", "SubChannel":"string", "Sector":"string", "Month":"dateTime", "ComponentKey":"string", "Amount":"double", "NumericCells":"int64", "MissingCells":"int64"},
    MEASURES: {"MetricKey":"string", "Section":"string", "Measure":"string", "Unit":"string", "Aggregation":"string", "CutoffFamily":"string", "NumeratorKey":"string", "DenominatorKey":"string", "SortIndex":"int64"},
    MONTHS: {"Month":"dateTime", "MonthLabel":"string", "Year":"int64", "MonthNumber":"int64", "MonthIndex":"int64"},
    PERIODS: {"Year":"int64", "PeriodType":"string", "PeriodKey":"string", "Label":"string", "SortIndex":"int64"},
    SERIES: {"SeriesID":"string", "SeriesKind":"string", "SourceRevisionID":"string", "SeriesLabel":"string", "SortIndex":"int64"},
    MODES: {"Mode":"string", "SortIndex":"int64"},
}
TABLES[REFERENCE] = dict(TABLES[FILES])
TABLES[AXIS] = dict(TABLES[MONTHS])

RULE_FIELDS = ["MetricKey","Section","Measure","Unit","Aggregation","CutoffFamily","NumeratorKey","NumeratorSection","NumeratorMeasure","NumeratorManufacturer","NumeratorRequireProduct","DenominatorKey","DenominatorSection","DenominatorMeasure","DenominatorManufacturer","DenominatorRequireProduct","SortIndex"]

def rules():
    product_units = ("product-units", "Pricing", "Product Selling units", "*", "true")
    abbott_units = ("abbott-units", "Pricing", "Product Selling units", "Abbott", "true")
    product_value = ("product-value", "Pricing", "Product Value £", "*", "true")
    abbott_value = ("abbott-value", "Pricing", "Product Value £", "Abbott", "true")
    ef_units = ("ef-ads-units", "Ex-Factory", "ADS Selling units", "*", "false")
    ef_value = ("ef-ads-value", "Ex-Factory", "ADS Value £", "*", "false")
    empty = ("", "", "", "", "false")
    records = [
        ("ims-market-units", "IMS / Market", "IMS Market Units", "Units", "SUM", "IMS", product_units, empty),
        ("ims-abbott-units", "IMS / Market", "IMS Abbott Units", "Units", "SUM", "IMS", abbott_units, empty),
        ("ims-volume-share", "IMS / Market", "IMS Abbott Volume Share", "%", "RATIO", "IMS", abbott_units, product_units),
        ("ims-market-value", "IMS / Market", "IMS Market Value", "£", "SUM", "IMS", product_value, empty),
        ("ims-value-share", "IMS / Market", "IMS Abbott Value Share", "%", "RATIO", "IMS", abbott_value, product_value),
        ("ef-selling-units", "Ex-Factory", "Ex-factory Selling Units", "Units", "SUM", "EF", ef_units, empty),
        ("ef-value", "Ex-Factory", "Ex-factory Value", "£", "SUM", "EF", ef_value, empty),
    ]
    return [dict(zip(RULE_FIELDS, [*r[:6], *r[6], *r[7], (i+1)*10], strict=True)) for i,r in enumerate(records)]
