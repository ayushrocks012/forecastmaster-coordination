"""Rebuild the two native TEST pages; preserve advanced/refresh/source payloads.

Only a thin report is packaged. No cached business data or company model export.
"""
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("frozen_report", HERE.parent / "report-native-r17/prepare_project.py")
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)
lit, field, proj, write = pp.literal, pp.field, pp.projection, pp.write
TEAL, INK, PALE = "#096B76", "#183B56", "#EAF3F6"
NAME = "ForecastMaster Native Review R17.2 TEST"


def visual(*args, **kwargs):
    v = pp.visual(*args, **kwargs)
    o = v["visual"]["visualContainerObjects"]
    o["title"][0]["properties"].update(fontColor={"solid":{"color":lit(INK)}}, alignment=lit("left"))
    o["border"] = [{"properties":{"show":lit(True),"color":{"solid":{"color":lit("#DAE4ED")}},"radius":lit(5)}}]
    return v


def button(name, label, x, y, w, action, target, h=40):
    v = visual(name,"actionButton",x,y,w,h)
    v["visual"].pop("query",None)
    # Microsoft button authoring pattern: show toggles unselected, formatting
    # under the default-state selector, actions at CONTAINER level.
    def state(properties):
        return [{"properties":{"show":lit(True)}},
                {"properties":properties,"selector":{"id":"default"}}]
    v["visual"]["objects"] = {
        "text":state({"text":lit(label),"fontSize":lit(11),
            "fontColor":{"solid":{"color":lit(TEAL)}},"horizontalAlignment":lit("center")}),
        "fill":state({"fillColor":{"solid":{"color":lit("#FFFFFF")}},"transparency":lit(0)}),
        "outline":state({"lineColor":{"solid":{"color":lit("#CBDEE5")}},"weight":lit(1)}),
        "icon":[{"properties":{"show":lit(False),"placement":lit("left")}}],
        "shape":[{"properties":{"tileShape":lit("rectangleRounded")}}]}
    container = v["visual"]["visualContainerObjects"]
    container["visualLink"]=[{"properties":{"show":lit(True),"type":lit(action),
        "navigationSection" if action=="PageNavigation" else "bookmark":lit(target)}}]
    container["background"]=[{"properties":{"show":lit(False)}}]
    container["border"]=[{"properties":{"show":lit(False)}}]
    return v


def slicer(name,table,column,x,y,w,title,default=None,**kwargs):
    v=pp.slicer(name,table,column,x,y,w,title,default,**kwargs)
    v["position"]["height"]=70
    v["visual"]["objects"]["items"]=[{"properties":{"fontSize":lit(11),"fontColor":{"solid":{"color":lit(INK)}}}}]
    v["visual"]["visualContainerObjects"]["title"][0]["properties"].update(fontSize=lit(10),fontColor={"solid":{"color":lit(INK)}})
    return v


def table(name,x,y,w,h,measures,title=""):
    v=visual(name,"tableEx",x,y,w,h,title,{"Values":{"projections":[proj("fm_native_measures",m,True,label) for m,label in measures]}})
    v["visual"]["objects"]={"columnHeaders":[{"properties":{"show":lit(False)}}],
        "values":[{"properties":{"fontSize":lit(11)}}],"total":[{"properties":{"totals":lit(False)}}]}
    return v


def matrix(name,x,y,w,h,rows,values,title="",periods=True):
    v=pp.matrix(name,x,y,w,h,rows,values,periods,title)
    if periods:v["visual"]["query"]["queryState"]["Columns"]["projections"][0]=proj("fm_native_periods","Label")
    for role in v["visual"]["query"]["queryState"].values():
        for projection in role.get("projections",[]):projection.pop("active",None)
    v["visual"]["objects"]["grid"][0]["properties"]["rowPadding"]=lit(3)
    v["visual"]["objects"]["rowHeaders"][0]["properties"]["stepped"]=lit(True)
    v["visual"]["objects"]["rowHeaders"][0]["properties"]["autoExpand"]=lit(True)
    v["visual"]["objects"]["columnHeaders"][0]["properties"]["autoExpand"]=lit(True)
    v["visual"]["objects"]["columnHeaders"][0]["properties"].update(autoSizeColumnWidth=lit(True),columnAdjustment=lit("growToFit"))
    v["visual"]["visualContainerObjects"]["stylePreset"]=[{"properties":{"name":lit("None")}}]
    v["visual"]["objects"]["subTotals"][0]["properties"].update(rowSubtotals=lit(False),columnSubtotals=lit(False))
    v["visual"]["objects"]["values"][0]["properties"]["decimalPlaces"]=lit(2)
    return v


def date_filter(year):
    return {"Version":2,"From":[{"Name":"x","Entity":"fm_review_months","Type":0}],"Where":[{"Condition":{"Between":{
        "Expression":{"Column":{"Expression":{"SourceRef":{"Source":"x"}},"Property":"Month"}},
        "LowerBound":{"Literal":{"Value":f"datetime'{year}-01-01T00:00:00'"}},
        "UpperBound":{"Literal":{"Value":f"datetime'{year}-12-01T00:00:00'"}}}}}]}


def make_page(key,title,affiliate,cycle,sop=False):
    page={"$schema":pp.SCHEMA+"page/2.1.0/schema.json","name":key,"displayName":title,
          "displayOption":"FitToWidth","height":1510,"width":1440}
    vs=[]
    def add(v):vs.append(v);return v
    add(button("nav_demand","Demand review",20,10,150,"PageNavigation","native_demand"))
    add(button("nav_sop","S&OP review",180,10,150,"PageNavigation","native_sop"))
    add(button("nav_export","Export data",1030,10,140,"PageNavigation","native_export"))
    add(button("nav_advanced","R16.6 workspace",1180,10,240,"PageNavigation","advancedreview"))
    heading=visual("heading","textbox",20,58,1400,60,"ForecastMaster · "+title+" · R17.2 TEST")
    heading["visual"].pop("query",None)
    heading["visual"]["visualContainerObjects"]["title"][0]["properties"]["fontSize"]=lit(19)
    add(heading)
    dates=add(slicer("review_months","fm_review_months","Month",20,128,500,"Review months",mode="Between"))
    dates["visual"]["objects"]["general"][0]["properties"]["filter"]={"filter":date_filter(cycle[:4])}
    add(slicer("currency","fm_native_currency","Currency",1020,128,180,"Currency","USD",single=True))
    add(button("rates_show","Plan rates",1220,151,200,"Bookmark",key+"_rates_show"))
    add(table("source_status",20,202,1400,31,[("N Source Caption","Saved sources")]))
    add(slicer("affiliate","fm_review_files","Country",20,244,270,"Affiliate",affiliate))
    add(slicer("cycle","fm_review_files","DemandCycle",302,244,270,"Demand cycle",cycle))
    if not sop:
        add(slicer("section","fm_native_metric","Section",584,244,270,"Section","IMS / Market"))
        add(slicer("metric","fm_native_metric","MetricLabel",866,244,270,"Measure","Market",single=True))
    add(slicer("display","fm_native_display","Display",1148,244,272,"Display","Units",single=True))
    band=visual("scope_heading","textbox",20,326,1400,38,"Growth drivers, sectors & review summary period")
    band["visual"].pop("query",None);add(band)
    for ident,col,x,w,label in (("drivers","GrowthDriver",20,440,"Growth drivers"),("tiers","SectorLabel",480,440,"Forecast tiers")):
        v=add(slicer(ident,"fm_native_scope",col,x,370,w,label));pp.measure_filter(v,"N Scope Available")
    v=add(slicer("periods","fm_native_periods","Label",940,370,480,"Review summary period",cycle[:4]+" FY"))
    pp.measure_filter(v,"N Period Available")
    for name,x in (("drivers",20),("tiers",480),("periods",940)):
        add(button(name+"_all","Select all",x,445,105,"Bookmark",key+"_"+name+"_all"))
        add(button(name+"_clear","Clear all",x+115,445,105,"Bookmark",key+"_"+name+"_clear"))
    if not sop:
        headline=matrix("headline",20,499,1400,167,[("fm_native_headline","Label")],[("N Headline Cell","Selected total")],"Review summary")
        headline["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"]={"expr":field("fm_native_measures","N Measure Caption",True)}
        add(headline)
        add(slicer("chart_trend","fm_native_chart_trend","Label",20,679,240,"Headline trend","12M",sync=False,single=True))
        add(slicer("trend","fm_native_trend","Label",280,679,320,"Trend comparisons",["12M"],sync=False))
        add(slicer("view","fm_native_view","View",620,679,370,"Chart view","Total",sync=False,single=True))
        add(slicer("file_mode","fm_native_file_mode","Mode",1010,679,410,"Plan source","Automatic ADS",single=True))
        chart=pp.chart("native_chart","demand",20,767,1400,310)
        chart["visual"]["query"]["queryState"]["Category"]["showAll"]=False
        pp.measure_filter(chart,"N Line Visible");add(chart)
        add(table("month_readout",20,1082,1400,38,[("N Selected Month","Month"),("N Selected Monthly","Selected monthly total")]))
        for i,(mode,rows) in enumerate({"drivers":[("fm_native_scope","GrowthDriver")],
            "sectors":[("fm_native_scope","SectorLabel")],"both":[("fm_native_scope","GrowthDriver"),("fm_native_scope","Sector")]}.items()):
            t=matrix("summary_"+mode,20,1185,1400,245,rows,[("N Summary Cell","Value")],"Executive summary")
            t["visual"]["query"]["queryState"]["Columns"]["projections"].extend([proj("fm_native_columns","Comparison"),proj("fm_native_columns","ValueLabel")])
            t["visual"]["objects"]["values"][0]["properties"]["fontColor"]={"solid":{"color":{"expr":field("fm_native_measures","N Variance Color",True)}}}
            if mode!="drivers":t["isHidden"]=True
            add(t);add(button("rows_"+mode,mode.title(),20+i*120,1135,110,"Bookmark","table_"+mode))
    else:
        add(slicer("view","fm_native_view","View",460,499,300,"Chart / table breakdown","Total",sync=False,single=True))
        add(slicer("runrate","fm_native_run_rate","Show",775,499,200,"Monthly run rate","Off",sync=False,single=True))
        add(slicer("growth","fm_native_growth","Show",990,499,200,"Growth vs PY","Off",sync=False,single=True))
        add(slicer("file_mode","fm_native_file_mode","Mode",1205,499,215,"Plan source","Automatic ADS",single=True))
        chart=pp.chart("native_chart","sop",460,586,960,320)
        chart["visual"]["query"]["queryState"]["Category"]["showAll"]=False
        pp.measure_filter(chart,"N Line Visible");add(chart)
        add(table("month_readout",460,911,960,38,[("N Selected Month","Selected month")]))
        rows=[("fm_native_groups","ScopeLabel")]+[("fm_native_rows",n) for n in ("Channel","SubChannel","Measure")]
        t=add(matrix("sop_summary",460,1010,960,420,rows,[("N SOP Plan","Plan"),("N SOP Run Rate","Monthly run rate"),("N SOP Growth %","Growth vs PY")],"S&OP summary"))
        pp.measure_filter(t,"N Group Visible")
        t=matrix("sop_monthly",460,1010,960,420,rows,[("N SOP Monthly","Amount"),("N SOP Monthly Growth %","Growth vs PY")],"S&OP summary · monthly",False)
        t["visual"]["query"]["queryState"]["Columns"]={"projections":[proj("fm_review_axis","Month")]}
        pp.measure_filter(t,"N Group Visible");t["isHidden"]=True;add(t)
        add(button("period_mode","Periods",460,960,110,"Bookmark","sop_periods"))
        add(button("monthly_mode","Monthly",580,960,110,"Bookmark","sop_monthly"))
        ctrl=visual("native_controls",pp.GUID,20,499,420,931,"Build your view",{n:{"projections":[proj("fm_native_catalog",n)]} for n in ("RowID","Channel","SubChannel","Measure","Display","ChannelRank","SubRank","MeasureRank")})
        ctrl["visual"]["objects"]={"general":[{"properties":{"currencies":lit("GBP"),"variant":lit("sop"),"filter":{"filter":pp.category_filter("fm_native_state","Token",["none"])}}}]}
        ctrl["visual"]["syncGroup"]={"groupName":"Native review preferences","fieldChanges":False,"filterChanges":True}
        pp.measure_filter(ctrl,"N Catalog Visible");pp.measure_filter(ctrl,"N Catalog Available");add(ctrl)
    add(slicer("matching_files","fm_review_files","FileLabel",20,1440,1400,"Matching files · optional source override",sync=True))
    # Focus mode supplies native full-canvas zoom without a second HTML viewport.
    gy=767 if not sop else 586
    sy=1135 if not sop else 960
    for group,y in (("graph",gy),("summary",sy)):
        add(button(group+"_hide","Hide "+group,1260,y+3,150,"Bookmark",key+"_"+group+"_hide"))
        t=add(button(group+"_show","Show "+group,1260,y+3,150,"Bookmark",key+"_"+group+"_show"));t["isHidden"]=True
    # Header-level plan-rate overlay: query-free metadata controller, initially hidden.
    ctrl=visual("fx_controls",pp.GUID,1000,111,420,170,"Plan exchange rates",{n:{"projections":[proj("fm_native_catalog",n)]} for n in ("RowID","Channel","SubChannel","Measure","Display","ChannelRank","SubRank","MeasureRank")})
    ctrl["visual"]["objects"]={"general":[{"properties":{"currencies":lit("GBP"),"variant":lit("fx"),"filter":{"filter":pp.category_filter("fm_native_state","Token",["none"])}}}]}
    ctrl["visual"]["syncGroup"]={"groupName":"Native review preferences","fieldChanges":False,"filterChanges":True}
    ctrl["isHidden"]=True;add(ctrl)
    t=add(button("rates_hide","Close rates",1220,283,200,"Bookmark",key+"_rates_hide"));t["isHidden"]=True
    # Chart selections show monthly readouts without silently changing totals.
    page["visualInteractions"]=[{"source":"native_chart","target":v["name"],"type":"DataFilter" if v["name"]=="month_readout" else "NoFilter"}
        for v in vs if v["name"]!="native_chart"]
    for i,v in enumerate(vs):v["position"].update(z=i,tabOrder=i)
    return page,vs


def selection_bookmark(page,target,table,column,clear):
    b=pp.selection_bookmark(page,"scope" if target=="drivers" else "periods",table,column,clear)
    b["name"]=page+"_"+target+("_clear" if clear else "_all")
    containers=b["explorationState"]["sections"][page]["visualContainers"]
    b["options"]["targetVisualNames"]=[target]
    b["explorationState"]["sections"][page]["visualContainers"]={target:next(iter(containers.values()))}
    # A driver selection should start with all tiers within the chosen driver.
    if target=="drivers":
        b["options"]["targetVisualNames"].append("tiers")
        b["explorationState"]["sections"][page]["visualContainers"]["tiers"]={"singleVisual":{"objects":{"remove":[{"object":"general","property":"filter","selector":{}}]}}}
    return b


def create(source_zip,destination,affiliate="UK",cycle="2026-10"):
    if destination.exists():raise ValueError("Use a new output folder; preserve earlier reports.")
    expected="49b14405b512e1693e649226d81ebcc7857ee55ff0aae6fd98d3223813859713"
    if hashlib.sha256(source_zip.read_bytes()).hexdigest()!=expected:raise ValueError("Unexpected frozen TEST report ZIP.")
    with TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as z:z.extractall(tmp)
        source=next(Path(tmp).glob("*.Report"));report=destination/(NAME+".Report")
        shutil.copytree(source,report)
        root=report/"definition";pages=root/"pages"
        config=json.loads((root/"report.json").read_text())
        theme_name="ForecastMasterNativeR172"
        write(report/"StaticResources/RegisteredResources/fm-native-r172-theme.json",{
            "name":"ForecastMaster native R17.2","dataColors":["#087F83","#087F83","#6B7280","#496A91","#7D61A8","#A56723","#517646","#B85C72"],
            "background":"#FFFFFF","foreground":INK,"tableAccent":TEAL,
            "textClasses":{"label":{"fontFace":"Segoe UI","fontSize":11,"color":INK},
                           "title":{"fontFace":"Segoe UI","fontSize":12,"color":INK}}})
        config.setdefault("themeCollection",{})["customTheme"]={"name":theme_name,"type":"RegisteredResources",
            "reportVersionAtImport":{"visual":"2.7.0","report":"3.4.0","page":"2.1.0"}}
        packages=config.setdefault("resourcePackages",[])
        package=next((r for r in packages if r["name"]=="RegisteredResources"),None)
        if package is None:
            package={"name":"RegisteredResources","type":"RegisteredResources","items":[]};packages.append(package)
        package["items"].append({"name":theme_name,"path":"fm-native-r172-theme.json","type":"CustomTheme"})
        write(root/"report.json",config)
        bookmarks=[];native={}
        for key,title,sop in (("native_demand","Demand review",False),("native_sop","S&OP review",True)):
            shutil.rmtree(pages/key)
            page,vs=make_page(key,title,affiliate,cycle,sop);native[key]=vs
            write(pages/key/"page.json",page)
            for v in vs:
                if v.get("visual",{}).get("visualType") in {"pivotTable","tableEx"}:
                    for role in v["visual"]["query"]["queryState"].values():
                        for projection in role.get("projections",[]):projection.pop("active",None)
                    if v["visual"]["visualType"]=="pivotTable":
                        v["visual"]["expansionStates"]=[{"roles":[name],"levels":[
                            {"queryRefs":[q["queryRef"]],"identityKeys":[q["field"]],"isCollapsed":False}
                            for q in role["projections"][:-1]]}
                            for name,role in v["visual"]["query"]["queryState"].items()
                            if name in {"Rows","Columns"} and len(role["projections"])>1]
                write(pages/key/"visuals"/v["name"]/"visual.json",v)
            for target,table_,column in (("drivers","fm_native_scope","GrowthDriver"),("tiers","fm_native_scope","SectorLabel"),("periods","fm_native_periods","Label")):
                for clear in (True,False):bookmarks.append(selection_bookmark(key,target,table_,column,clear))
            for hidden in (True,False):
                bookmarks.append(pp.visibility_bookmark(key+"_rates_"+("hide" if hidden else "show"),key,
                    ["rates_show"] if hidden else ["fx_controls","rates_hide"],
                    ["fx_controls","rates_hide"] if hidden else ["rates_show"]))
                bookmarks.append(pp.visibility_bookmark(key+"_graph_"+("hide" if hidden else "show"),key,
                    ["graph_show"] if hidden else ["native_chart","graph_hide","month_readout"],
                    ["native_chart","graph_hide","month_readout"] if hidden else ["graph_show"]))
                # Independent summary row/period mode bookmarks remain intact.
                targets=["sop_summary","sop_monthly","period_mode","monthly_mode"] if sop else ["summary_drivers","summary_sectors","summary_both","rows_drivers","rows_sectors","rows_both"]
                default="sop_summary" if sop else "summary_drivers"
                visible=["summary_show"] if hidden else ["summary_hide",default]+[x for x in targets if x.startswith(("rows_","period_","monthly_"))]
                hidden_names=["summary_hide"]+targets if hidden else ["summary_show"]+[x for x in targets if x not in visible]
                bookmarks.append(pp.visibility_bookmark(key+"_summary_"+("hide" if hidden else "show"),key,visible,hidden_names))
        for mode in ("drivers","sectors","both"):
            bookmarks.append(pp.visibility_bookmark("table_"+mode,"native_demand",["summary_"+mode],["summary_"+m for m in ("drivers","sectors","both") if m!=mode]))
        for mode in ("periods","monthly"):
            bookmarks.append(pp.visibility_bookmark("sop_"+mode,"native_sop",["sop_summary" if mode=="periods" else "sop_monthly"],["sop_monthly" if mode=="periods" else "sop_summary"]))
        shutil.rmtree(root/"bookmarks")
        for b in bookmarks:write(root/"bookmarks"/(b["name"]+".bookmark.json"),b)
        write(root/"bookmarks/bookmarks.json",{"$schema":pp.SCHEMA+"bookmarksMetadata/1.0.0/schema.json","items":[{"name":b["name"]} for b in bookmarks]})
        # Refresh all hidden native export filter mirrors to the revised controls.
        ep=pages/"native_export"/"visuals"
        for p in list(ep.glob("*/visual.json")):
            value=json.loads(p.read_text())
            if value.get("isHidden"):shutil.rmtree(p.parent)
            elif value.get("visual",{}).get("visualType")=="actionButton":
                old=value["visual"]["objects"]["visualLink"][0]["properties"]
                label=value["visual"]["objects"]["text"][0]["properties"]["text"]["expr"]["Literal"]["Value"][1:-1]
                value=button(value["name"],label,**{k:value["position"][k] for k in ("x","y")},w=value["position"]["width"],action="PageNavigation",target=old["navigationSection"]["expr"]["Literal"]["Value"][1:-1])
                write(p,value)
            else:
                value=json.loads(json.dumps(value).replace("fm_review_periods","fm_native_periods"))
                for role in value["visual"].get("query",{}).get("queryState",{}).values():
                    for projection in role.get("projections",[]):projection.pop("active",None)
                write(p,value)
        seen=set()
        for v in native["native_sop"]+native["native_demand"]:
            group=v.get("visual",{}).get("syncGroup",{}).get("groupName")
            if not group or group in seen:continue
            seen.add(group);v=deepcopy(v);v["isHidden"]=True
            write(ep/v["name"]/"visual.json",v)
        write(destination/(NAME+".pbip"),{"$schema":"https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json","version":"1.0","artifacts":[{"report":{"path":report.name}}],"settings":{"enableAutoRecovery":True}})
        # All advanced/refresh visual payloads, custom code, and TEST binding unchanged.
        preserved={}
        for folder in ("definition/pages/advancedreview","definition/pages/refreshdemand","CustomVisuals"):
            for p in (source/folder).rglob("*"):
                if p.is_file():
                    rel=p.relative_to(source)
                    assert p.read_bytes()==(report/rel).read_bytes()
                    preserved[str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
        assert (source/"definition.pbir").read_bytes()==(report/"definition.pbir").read_bytes()
        return {"FrozenSourceZIP":expected,"PreservedPayloads":preserved,"TESTBindingPreserved":True,"CompanyModelIncluded":False,
                "DesktopRendering":"PENDING","ProductionReplacement":"NOT QUALIFIED"}


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("source",type=Path);p.add_argument("destination",type=Path)
    a=p.parse_args();receipt=create(a.source,a.destination)
    write(a.destination/"PRESERVATION.json",receipt)
    print(a.destination)
