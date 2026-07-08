from __future__ import annotations
import math
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="BlueCarbonCell OS v3", page_icon="🌊", layout="wide")
st.markdown("""
<style>
.big{font-size:2.4rem;font-weight:850;color:#00305E}.sub{color:#555;font-size:1.05rem}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="big">BlueCarbonCell OS v3</div>', unsafe_allow_html=True)
st.markdown('<div class="sub">Advanced research MVP for MCFC ship retrofit feasibility, sizing, uncertainty, pilot planning and spin-off demonstration</div>', unsafe_allow_html=True)
st.info('Research prototype only. It supports preliminary feasibility assessment and does not replace MCFC experiments, naval design, safety assessment, classification approval or pilot validation.')

F=96485.3329
MW_CO2_KG_MOL=0.04401
MW_CO2=44.01
MW_OTHER=29.0
CP_EXH=1.05

SHIP_PRESETS={
 'Cargo ship':(8,4500,18,6,350),'Ferry':(5,3500,12,5.5,330),'Cruise ship':(25,5000,65,6.5,360),
 'Tanker':(15,5200,40,6.2,370),'Ro-Ro vessel':(10,4200,25,5.8,340),'Research vessel':(3,2500,7,5,310),'Custom':(8,4500,18,6,350)}
PROFILE_PRESETS={'Open-sea cruising':(85,2400,75),'Slow steaming':(75,2200,70),'Port / hotel load':(45,1600,50),'Mixed operation':(65,2500,65),'Manoeuvring':(30,1800,35),'User-defined':(65,2500,65)}

def clamp(x,a,b): return max(a,min(b,x))
def co2_mass_frac(xvol):
    x=clamp(xvol,0,1); return (x*MW_CO2)/(x*MW_CO2+(1-x)*MW_OTHER)
def thermal_score(temp,tmin,tmax):
    if tmin<=temp<=tmax: return 100,'Good thermal match'
    if temp<tmin: return clamp(100*(temp-(tmin-280))/280,0,100),'Too cold; preheating or thermal buffering may be needed'
    return clamp(100*((tmax+180)-temp)/180,0,100),'Too hot; bypass/dilution/heat exchange may be needed'
def pressure_score(loss,limit):
    if limit<=0: return 0,'Invalid pressure limit'
    ratio=loss/limit; score=clamp(100*(1-ratio),0,100)
    if ratio<=0.4: msg='Low pressure-loss risk'
    elif ratio<=0.8: msg='Moderate pressure-loss risk'
    elif ratio<=1.0: msg='High but below limit'
    else: msg='Critical: pressure-loss limit exceeded'
    return score,msg
def category(score):
    return 'High preliminary feasibility' if score>=78 else 'Moderate preliminary feasibility' if score>=60 else 'Low-to-moderate feasibility' if score>=42 else 'Low preliminary feasibility'

def calc(p):
    mf=co2_mass_frac(p['co2']/100)
    co2_flow=p['flow']*mf
    annual_co2=co2_flow*3600*p['hours']/1000
    eff=(p['capture']/100)*(p['availability']/100)*(0.75+0.25*p['stable']/100)
    captured=annual_co2*eff
    remaining=annual_co2-captured
    heat_kw=p['flow']*CP_EXH*p['dT']*(p['heat_eff']/100)
    heat_mwh=heat_kw*p['hours']/1000
    elec_mwh=p['power_kw']*p['hours']*(p['availability']/100)/1000
    th,thmsg=thermal_score(p['temp'],p['tmin'],p['tmax'])
    pr,prmsg=pressure_score(p['pressure_loss'],p['pressure_limit'])
    simplicity=100-p['complexity']
    feasibility=.20*p['capture']+.18*th+.16*pr+.11*p['heat_eff']+.10*p['stable']+.09*p['compact']+.08*p['safety']+.04*p['data_quality']+.04*simplicity
    pilot=.28*feasibility+.20*p['data_quality']+.18*p['safety']+.14*th+.12*pr+.08*p['compact']
    value=captured*p['carbon_value']+heat_mwh*p['heat_value']+elec_mwh*p['electricity_value']
    payback=p['capex']/value if value>0 else np.nan
    return dict(co2_mass_fraction=mf,co2_flow=co2_flow,annual_co2=annual_co2,captured=captured,remaining=remaining,effective_capture=eff*100,heat_kw=heat_kw,heat_mwh=heat_mwh,elec_mwh=elec_mwh,thermal=th,thermal_msg=thmsg,pressure=pr,pressure_msg=prmsg,feasibility=feasibility,pilot=pilot,category=category(feasibility),annual_value=value,payback=payback,simplicity=simplicity)

def sizing(p,r):
    target_kg_s=r['co2_flow']*(p['capture']/100)
    mol_s=target_kg_s/MW_CO2_KG_MOL
    current=2*F*mol_s
    area=current/max(p['current_density'],1e-9)
    power=current*p['cell_voltage']/1000
    nmods=max(1,math.ceil(power/max(p['module_power'],1e-9)))
    volume=power/max(p['vol_power_density'],1e-9)
    mass=power*p['specific_mass']/1000
    footprint=volume/max(p['height'],1e-9)
    return dict(target_kg_s=target_kg_s,mol_s=mol_s,current=current,area=area,faraday_power=power,nmods=nmods,volume=volume,mass=mass,footprint=footprint)

def hx_calc(p,r):
    q=r['heat_kw']; hot_in=p['temp']; hot_out=max(20,hot_in-p['dT']); cold_in=p['cool_in']; cold_out=p['cool_out']
    dt1=hot_in-cold_out; dt2=hot_out-cold_in
    lmtd=np.nan; ua=np.nan
    if dt1>0 and dt2>0:
        lmtd=dt1 if abs(dt1-dt2)<1e-9 else (dt1-dt2)/math.log(dt1/dt2)
        ua=q/lmtd if lmtd>0 else np.nan
    return dict(q=q,hot_in=hot_in,hot_out=hot_out,cold_in=cold_in,cold_out=cold_out,lmtd=lmtd,ua=ua)

def profile_df(profile,flow,temp,co2):
    h=np.arange(24)
    if profile=='Open-sea cruising': load=.82+.04*np.sin(h/24*2*np.pi)
    elif profile=='Slow steaming': load=.55+.05*np.sin(h/24*2*np.pi)
    elif profile=='Port / hotel load': load=.28+.06*np.sin(h/24*4*np.pi)
    elif profile=='Manoeuvring': load=np.clip(.45+.20*np.sin(h/24*8*np.pi),.15,.85)
    else: load=np.array([.25,.25,.30,.45,.65,.80,.85,.85,.82,.78,.75,.70,.65,.70,.75,.80,.82,.72,.55,.45,.35,.30,.28,.25])
    return pd.DataFrame({'hour':h,'engine_load_fraction':load,'exhaust_flow_kg_s':flow*(.35+.75*load),'exhaust_temp_c':temp*(.65+.45*load),'co2_vol_percent':co2*(.85+.25*load)})

def dynamic_results(df,p):
    rows=[]
    for _,row in df.iterrows():
        pp=p.copy(); pp['flow']=float(row.exhaust_flow_kg_s); pp['temp']=float(row.exhaust_temp_c); pp['co2']=float(row.co2_vol_percent); pp['hours']=1
        rr=calc(pp)
        rows.append({'hour':row.hour,'engine_load_fraction':row.engine_load_fraction,'exhaust_temp_c':row.exhaust_temp_c,'co2_vol_percent':row.co2_vol_percent,'co2_produced_t_h':rr['annual_co2'],'co2_captured_t_h':rr['captured'],'heat_mwh_h':rr['heat_mwh'],'feasibility':rr['feasibility']})
    return pd.DataFrame(rows)

def monte_carlo(p,n,unc,seed=42):
    rng=np.random.default_rng(seed)
    keys=['flow','co2','capture','temp','pressure_loss','heat_eff','dT','compact','safety']
    rows=[]
    for i in range(n):
        pp=p.copy()
        for k in keys:
            v=float(p[k]); s=rng.normal(v,max(abs(v)*unc,1e-9))
            if k in ['co2','capture','heat_eff','compact','safety']: s=clamp(s,.1,99.9)
            elif k=='temp': s=clamp(s,50,900)
            else: s=max(.001,s)
            pp[k]=s
        rr=calc(pp); ss=sizing(pp,rr)
        rows.append({'run':i+1,'captured_co2_t':rr['captured'],'heat_mwh':rr['heat_mwh'],'electricity_mwh':rr['elec_mwh'],'feasibility':rr['feasibility'],'pilot':rr['pilot'],'payback':rr['payback'],'active_area_m2':ss['area'],'module_volume_m3':ss['volume']})
    return pd.DataFrame(rows)

def tornado(p):
    base=calc(p)['feasibility']
    vars={'Capture efficiency':('capture',.20),'Exhaust temp':('temp',.15),'Pressure loss':('pressure_loss',.25),'Heat efficiency':('heat_eff',.20),'Stable operation':('stable',.20),'Compactness':('compact',.20),'Safety':('safety',.20)}
    rows=[]
    for label,(key,d) in vars.items():
        lo=p.copy(); hi=p.copy(); lo[key]=max(.001,p[key]*(1-d)); hi[key]=p[key]*(1+d)
        if key in ['capture','heat_eff','stable','compact','safety']:
            lo[key]=clamp(lo[key],.1,99.9); hi[key]=clamp(hi[key],.1,99.9)
        rows.append({'Variable':label,'Low':calc(lo)['feasibility'],'High':calc(hi)['feasibility'],'Base':base})
    out=pd.DataFrame(rows); out['Range']=abs(out.High-out.Low)
    return out.sort_values('Range')

def report(p,r,s,hx):
    return f"""# BlueCarbonCell OS v3 - Preliminary MCFC Ship Retrofit Report

## Scenario
- Ship type: {p['ship']}
- Fuel type: {p['fuel']}
- Operating profile: {p['profile']}
- Engine power: {p['engine_power']:.2f} MW
- Annual operating hours: {p['hours']:.0f} h/year
- Exhaust temperature: {p['temp']:.1f} °C
- Exhaust mass flow: {p['flow']:.2f} kg/s
- CO₂ concentration: {p['co2']:.2f} vol%

## Estimated performance
- Annual CO₂ produced: {r['annual_co2']:,.1f} tCO₂/year
- Annual CO₂ captured: {r['captured']:,.1f} tCO₂/year
- Annual CO₂ remaining: {r['remaining']:,.1f} tCO₂/year
- Annual heat recovery: {r['heat_mwh']:,.1f} MWh/year
- Annual electricity estimate: {r['elec_mwh']:,.1f} MWh/year

## Preliminary sizing
- Target captured CO₂ flow: {s['target_kg_s']:.3f} kg/s
- Required current proxy: {s['current']:,.0f} A
- Estimated active area: {s['area']:,.1f} m²
- Gross power proxy: {s['faraday_power']:,.1f} kW
- Estimated modules: {s['nmods']}
- Volume: {s['volume']:,.1f} m³
- Mass: {s['mass']:,.1f} t
- Footprint: {s['footprint']:,.1f} m²

## Heat integration
- Recovered heat: {hx['q']:,.1f} kW
- Hot inlet/outlet: {hx['hot_in']:.1f}/{hx['hot_out']:.1f} °C
- LMTD: {hx['lmtd'] if not pd.isna(hx['lmtd']) else 'invalid'} K
- UA: {hx['ua'] if not pd.isna(hx['ua']) else 'invalid'} kW/K

## Feasibility
- Final feasibility score: {r['feasibility']:.1f}/100
- Pilot-readiness score: {r['pilot']:.1f}/100
- Category: {r['category']}
- Thermal interpretation: {r['thermal_msg']}
- Pressure interpretation: {r['pressure_msg']}

## Disclaimer
This report is generated by an early-stage research MVP. It does not replace detailed MCFC experiments, naval engineering design, safety analysis, classification approval or pilot validation.
"""

# Sidebar
st.sidebar.header('Scenario presets')
ship=st.sidebar.selectbox('Ship type',list(SHIP_PRESETS.keys()))
fuel=st.sidebar.selectbox('Fuel type',['Marine diesel oil / MGO','Heavy fuel oil / HFO','LNG','Methanol','User-defined'])
profile=st.sidebar.selectbox('Operating profile',list(PROFILE_PRESETS.keys()))
sp=SHIP_PRESETS[ship]; pr=PROFILE_PRESETS[profile]
st.sidebar.header('1. Ship and exhaust')
engine_power=st.sidebar.number_input('Engine power [MW]',.1,150.0,float(sp[0]),step=.5)
hours=st.sidebar.number_input('Annual operating hours [h/y]',100.0,8760.0,float(sp[1]),step=100.0)
flow=st.sidebar.number_input('Exhaust mass flow [kg/s]',.1,500.0,float(sp[2]),step=.5)
co2=st.sidebar.slider('CO₂ concentration [vol%]',1.0,20.0,float(sp[3]),step=.1)
temp=st.sidebar.number_input('Exhaust temperature [°C]',50.0,900.0,float(sp[4]),step=10.0)
st.sidebar.header('2. MCFC module')
capture=st.sidebar.slider('Nominal capture efficiency [%]',5.0,95.0,60.0,step=1.0)
power_kw=st.sidebar.number_input('Nominal MCFC electrical output [kW]',0.0,50000.0,500.0,step=50.0)
availability=st.sidebar.slider('MCFC availability [%]',0.0,100.0,float(pr[2]),step=1.0)
cell_voltage=st.sidebar.number_input('Cell voltage proxy [V]',.1,1.5,.75,step=.05)
current_density=st.sidebar.number_input('Current density proxy [A/m²]',100.0,5000.0,1500.0,step=100.0)
module_power=st.sidebar.number_input('Single module size [kW]',10.0,5000.0,250.0,step=10.0)
vol_power_density=st.sidebar.number_input('Volumetric power density [kW/m³]',1.0,1000.0,80.0,step=5.0)
specific_mass=st.sidebar.number_input('Specific mass [kg/kW]',1.0,100.0,12.0,step=1.0)
height=st.sidebar.number_input('Module height [m]',.5,5.0,2.2,step=.1)
st.sidebar.header('3. Heat and pressure')
heat_eff=st.sidebar.slider('Heat recovery efficiency [%]',0.0,95.0,45.0,step=1.0)
dT=st.sidebar.number_input('Recoverable exhaust ΔT [°C]',0.0,450.0,120.0,step=10.0)
cool_in=st.sidebar.number_input('Coolant inlet [°C]',0.0,200.0,70.0,step=5.0)
cool_out=st.sidebar.number_input('Coolant outlet [°C]',0.0,250.0,120.0,step=5.0)
pressure_loss=st.sidebar.number_input('Pressure loss [Pa]',0.0,30000.0,float(pr[1]),step=100.0)
pressure_limit=st.sidebar.number_input('Pressure-loss limit [Pa]',100.0,30000.0,5000.0,step=100.0)
tmin=st.sidebar.number_input('MCFC temp min [°C]',300.0,900.0,580.0,step=10.0)
tmax=st.sidebar.number_input('MCFC temp max [°C]',300.0,900.0,700.0,step=10.0)
st.sidebar.header('4. Integration and economics')
stable=st.sidebar.slider('Stable operation share [%]',0.0,100.0,float(pr[0]),step=1.0)
compact=st.sidebar.slider('Compactness / space score [%]',0.0,100.0,55.0,step=1.0)
safety=st.sidebar.slider('Safety integration score [%]',0.0,100.0,55.0,step=1.0)
data_quality=st.sidebar.slider('Data quality score [%]',0.0,100.0,60.0,step=1.0)
complexity=st.sidebar.slider('Retrofit complexity [higher is worse, %]',0.0,100.0,45.0,step=1.0)
carbon_value=st.sidebar.number_input('Carbon value [€/tCO₂]',0.0,500.0,80.0,step=5.0)
electricity_value=st.sidebar.number_input('Electricity value [€/MWh]',0.0,500.0,130.0,step=5.0)
heat_value=st.sidebar.number_input('Recovered heat value [€/MWh]',0.0,300.0,45.0,step=5.0)
capex=st.sidebar.number_input('Indicative CAPEX [€]',10000.0,200000000.0,1500000.0,step=50000.0)
annual_co2_reference_t=0.0

p=dict(ship=ship,fuel=fuel,profile=profile,engine_power=engine_power,hours=hours,flow=flow,co2=co2,temp=temp,capture=capture,power_kw=power_kw,availability=availability,cell_voltage=cell_voltage,current_density=current_density,module_power=module_power,vol_power_density=vol_power_density,specific_mass=specific_mass,height=height,heat_eff=heat_eff,dT=dT,cool_in=cool_in,cool_out=cool_out,pressure_loss=pressure_loss,pressure_limit=pressure_limit,tmin=tmin,tmax=tmax,stable=stable,compact=compact,safety=safety,data_quality=data_quality,complexity=complexity,carbon_value=carbon_value,electricity_value=electricity_value,heat_value=heat_value,capex=capex,annual_co2_reference_t=annual_co2_reference_t)
r=calc(p); s=sizing(p,r); h=hx_calc(p,r); prof=profile_df(profile,flow,temp,co2); dyn=dynamic_results(prof,p)

tabs=st.tabs(['Executive dashboard','MCFC sizing','Thermal integration','Dynamic operation','Feasibility','Uncertainty','Scenario comparison','Pilot monitoring plan','Report'])
with tabs[0]:
    st.subheader('Executive dashboard')
    cols=st.columns(4)
    cols[0].metric('Feasibility',f"{r['feasibility']:.1f}/100")
    cols[1].metric('Pilot readiness',f"{r['pilot']:.1f}/100")
    cols[2].metric('Captured CO₂',f"{r['captured']:,.0f} t/y")
    cols[3].metric('Heat recovery',f"{r['heat_mwh']:,.0f} MWh/y")
    cols=st.columns(4)
    cols[0].metric('CO₂ produced',f"{r['annual_co2']:,.0f} t/y")
    cols[1].metric('MCFC electricity',f"{r['elec_mwh']:,.0f} MWh/y")
    cols[2].metric('Module volume',f"{s['volume']:,.1f} m³")
    cols[3].metric('Payback proxy',f"{r['payback']:.1f} y")
    st.markdown(f"### Decision category: **{r['category']}**")
    st.write('**Thermal:** '+r['thermal_msg']); st.write('**Pressure:** '+r['pressure_msg'])
    fig=px.pie(pd.DataFrame({'Category':['Captured','Remaining'],'tCO₂/year':[r['captured'],r['remaining']]}),names='Category',values='tCO₂/year',title='CO₂ captured vs remaining')
    st.plotly_chart(fig,use_container_width=True)
    st.code('Ship exhaust → CO₂ flow → MCFC capture → module sizing → heat integration → dynamic profile → uncertainty → feasibility + pilot readiness',language='text')
with tabs[1]:
    st.subheader('MCFC preliminary sizing')
    c=st.columns(4); c[0].metric('Target captured CO₂ flow',f"{s['target_kg_s']:.3f} kg/s"); c[1].metric('Required current',f"{s['current']:,.0f} A"); c[2].metric('Active area',f"{s['area']:,.1f} m²"); c[3].metric('Gross power proxy',f"{s['faraday_power']:,.0f} kW")
    c=st.columns(4); c[0].metric('Modules',s['nmods']); c[1].metric('Volume',f"{s['volume']:,.1f} m³"); c[2].metric('Mass',f"{s['mass']:,.1f} t"); c[3].metric('Footprint',f"{s['footprint']:,.1f} m²")
    df=pd.DataFrame({'Indicator':['Active area','Power proxy','Volume','Mass','Footprint'],'Value':[s['area'],s['faraday_power'],s['volume'],s['mass'],s['footprint']]})
    st.plotly_chart(px.bar(df,x='Indicator',y='Value',title='Preliminary module sizing indicators'),use_container_width=True)
    st.caption('Sizing uses a transparent Faraday-law proxy. It should be refined with validated MCFC cell/stack models.')
with tabs[2]:
    st.subheader('Thermal integration')
    c=st.columns(4); c[0].metric('Recovered heat',f"{h['q']:,.0f} kW"); c[1].metric('Hot outlet',f"{h['hot_out']:.1f} °C"); c[2].metric('LMTD','Invalid' if pd.isna(h['lmtd']) else f"{h['lmtd']:.1f} K"); c[3].metric('UA','Invalid' if pd.isna(h['ua']) else f"{h['ua']:.1f} kW/K")
    sankey=go.Figure(data=[go.Sankey(node=dict(label=['Ship exhaust','MCFC module','Recovered heat','Electricity','Remaining exhaust','Captured CO₂']),link=dict(source=[0,0,1,1,1],target=[1,4,2,3,5],value=[100,25,30,15,30]))])
    sankey.update_layout(title_text='Conceptual carbon-energy flow map')
    st.plotly_chart(sankey,use_container_width=True)
with tabs[3]:
    st.subheader('Dynamic operation profile')
    st.plotly_chart(px.line(prof,x='hour',y='engine_load_fraction',markers=True,title='24-hour engine load profile'),use_container_width=True)
    fig=go.Figure(); fig.add_trace(go.Scatter(x=prof.hour,y=prof.exhaust_temp_c,mode='lines+markers',name='Exhaust temp [°C]')); fig.add_trace(go.Scatter(x=prof.hour,y=prof.co2_vol_percent,mode='lines+markers',name='CO₂ [vol%]',yaxis='y2')); fig.update_layout(title='Dynamic exhaust conditions',xaxis_title='Hour',yaxis=dict(title='Temp [°C]'),yaxis2=dict(title='CO₂ [vol%]',overlaying='y',side='right'))
    st.plotly_chart(fig,use_container_width=True)
    st.plotly_chart(px.line(dyn,x='hour',y=['co2_captured_t_h','heat_mwh_h'],markers=True,title='Hourly capture and heat recovery proxy'),use_container_width=True)
    st.dataframe(dyn,use_container_width=True)
    st.download_button('Download dynamic profile CSV',dyn.to_csv(index=False).encode(),'bluecarboncell_dynamic_profile.csv','text/csv')
with tabs[4]:
    st.subheader('Feasibility score')
    score_df=pd.DataFrame({'Indicator':['CO₂ capture','Thermal match','Pressure safety','Heat recovery','Operational stability','Compactness','Safety','Data quality','Retrofit simplicity','Final feasibility','Pilot readiness'],'Score':[p['capture'],r['thermal'],r['pressure'],p['heat_eff'],p['stable'],p['compact'],p['safety'],p['data_quality'],r['simplicity'],r['feasibility'],r['pilot']]})
    st.plotly_chart(px.bar(score_df,x='Indicator',y='Score',range_y=[0,100],title='Score breakdown'),use_container_width=True)
    if r['feasibility']>=78: st.success('Strong preliminary case for deeper modelling and pilot feasibility discussion.')
    elif r['feasibility']>=60: st.warning('Moderate case. Improve thermal match, pressure loss, compactness, safety assumptions or data quality.')
    elif r['feasibility']>=42: st.warning('Low-to-moderate case. Redesign or better operating window is needed.')
    else: st.error('Low feasibility. This scenario is not yet suitable for pilot exploration.')
with tabs[5]:
    st.subheader('Uncertainty and sensitivity')
    c1,c2=st.columns(2); n=c1.slider('Monte Carlo simulations',200,10000,1500,step=100); unc=c2.slider('Input uncertainty [% standard deviation]',1,45,12,step=1)/100
    mc=monte_carlo(p,n,unc)
    c=st.columns(4); c[0].metric('Median feasibility',f"{mc.feasibility.median():.1f}"); c[1].metric('P05 feasibility',f"{mc.feasibility.quantile(.05):.1f}"); c[2].metric('P95 feasibility',f"{mc.feasibility.quantile(.95):.1f}"); c[3].metric('Median volume',f"{mc.module_volume_m3.median():.1f} m³")
    st.plotly_chart(px.histogram(mc,x='feasibility',nbins=40,title='Monte Carlo feasibility distribution'),use_container_width=True)
    st.plotly_chart(px.scatter(mc,x='captured_co2_t',y='feasibility',color='module_volume_m3',title='Captured CO₂ vs feasibility under uncertainty'),use_container_width=True)
    tor=tornado(p); fig=go.Figure(); fig.add_trace(go.Bar(y=tor.Variable,x=tor.High-tor.Base,orientation='h',name='+ variation')); fig.add_trace(go.Bar(y=tor.Variable,x=tor.Low-tor.Base,orientation='h',name='- variation')); fig.update_layout(title='Tornado-style sensitivity',xaxis_title='Change in feasibility score',barmode='overlay')
    st.plotly_chart(fig,use_container_width=True)
    st.download_button('Download Monte Carlo CSV',mc.to_csv(index=False).encode(),'bluecarboncell_monte_carlo.csv','text/csv')
with tabs[6]:
    st.subheader('Scenario comparison')
    example=pd.DataFrame([{'scenario':'Base cargo','ship':'Cargo ship','profile':'Open-sea cruising','engine_power':8,'hours':4500,'temp':350,'flow':18,'co2':6,'capture':60,'power_kw':500,'availability':70,'heat_eff':45,'dT':120,'pressure_loss':2500,'pressure_limit':5000,'tmin':580,'tmax':700,'stable':70,'compact':55,'safety':55,'data_quality':60,'complexity':45},{'scenario':'Thermally matched retrofit','ship':'Cargo ship','profile':'Open-sea cruising','engine_power':8,'hours':4500,'temp':610,'flow':18,'co2':6,'capture':75,'power_kw':700,'availability':75,'heat_eff':55,'dT':140,'pressure_loss':2300,'pressure_limit':5000,'tmin':580,'tmax':700,'stable':85,'compact':65,'safety':65,'data_quality':70,'complexity':35},{'scenario':'Port load','ship':'Ferry','profile':'Port / hotel load','engine_power':3,'hours':3000,'temp':260,'flow':7,'co2':5,'capture':45,'power_kw':250,'availability':50,'heat_eff':35,'dT':80,'pressure_loss':1800,'pressure_limit':4000,'tmin':580,'tmax':700,'stable':45,'compact':60,'safety':60,'data_quality':55,'complexity':50}])
    st.download_button('Download scenario template CSV',example.to_csv(index=False).encode(),'bluecarboncell_scenario_template.csv','text/csv')
    up=st.file_uploader('Upload scenario CSV',type=['csv'])
    scen=pd.read_csv(up) if up else example.copy(); rows=[]
    for _,row in scen.iterrows():
        pp=p.copy()
        for col in scen.columns:
            if col in pp: pp[col]=row[col]
        rr=calc(pp); ss=sizing(pp,rr)
        rows.append({'scenario':row.get('scenario','Unnamed'),'captured_co2_t':rr['captured'],'heat_mwh':rr['heat_mwh'],'electricity_mwh':rr['elec_mwh'],'feasibility':rr['feasibility'],'pilot':rr['pilot'],'module_volume_m3':ss['volume'],'category':rr['category']})
    comp=pd.DataFrame(rows); st.dataframe(comp,use_container_width=True)
    st.plotly_chart(px.bar(comp,x='scenario',y='feasibility',color='category',range_y=[0,100],title='Scenario feasibility comparison'),use_container_width=True)
    st.plotly_chart(px.scatter(comp,x='captured_co2_t',y='feasibility',size='module_volume_m3',color='category',hover_name='scenario',title='CO₂ captured vs feasibility'),use_container_width=True)
    st.download_button('Download scenario comparison CSV',comp.to_csv(index=False).encode(),'bluecarboncell_scenario_results.csv','text/csv')
with tabs[7]:
    st.subheader('Pilot monitoring and sensor plan')
    sensors=pd.DataFrame([['Exhaust inlet','Temperature','High-temperature thermocouple','Thermal matching and safety'],['Exhaust inlet','Flow rate','Flow meter or engine data proxy','CO₂ flow and pressure calculations'],['Exhaust inlet/outlet','CO₂ concentration','NDIR CO₂ analyser','Capture performance'],['MCFC stack','Stack temperature','Thermocouple array','Thermal-gradient monitoring'],['MCFC stack','Voltage/current','Electrical monitoring','Electrochemical performance'],['Gas channels','Pressure drop','Differential pressure sensor','Engine compatibility and safety'],['Heat recovery','Inlet/outlet temperatures','Temperature sensors','Recovered heat calculation'],['CO₂ outlet','CO₂-rich stream flow','Gas flow plus analyser','Captured carbon quantification'],['Control/safety','Bypass state','Valve position feedback','Operational safety'] ],columns=['Area','Variable','Sensor','Purpose'])
    st.dataframe(sensors,use_container_width=True)
    control=pd.DataFrame([['Stable cruising and suitable temperature','Run MCFC capture at target load'],['Exhaust temperature below MCFC window','Use preheating/thermal buffering or reduce capture load'],['Pressure loss close to limit','Open bypass or reduce flow through module'],['Rapid manoeuvring','Switch to partial load or standby'],['Stack thermal gradient too high','Adjust flow distribution and heat recovery'],['Sensor anomaly','Move to safe bypass and diagnostic mode']],columns=['Condition','Suggested action'])
    st.dataframe(control,use_container_width=True)
    st.download_button('Download sensor plan CSV',sensors.to_csv(index=False).encode(),'bluecarboncell_sensor_plan.csv','text/csv')
with tabs[8]:
    st.subheader('Downloadable report')
    rep=report(p,r,s,h); st.markdown(rep)
    full=pd.DataFrame([{**p,**r,**s,**h}])
    st.download_button('Download report as Markdown',rep.encode(),'bluecarboncell_v3_report.md','text/markdown')
    st.download_button('Download full results CSV',full.to_csv(index=False).encode(),'bluecarboncell_v3_results.csv','text/csv')

st.markdown('---')
st.caption('BlueCarbonCell OS v3 — advanced research MVP for PhD proposal, prototype demonstration and future spin-off discussion.')
