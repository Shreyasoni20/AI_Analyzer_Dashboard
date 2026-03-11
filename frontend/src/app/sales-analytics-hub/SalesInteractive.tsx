"use client"

import Header from "@/components/common/Header"

const pipeline = [
{stage:"Prospecting", deals:312, amount:"$11.8M"},
{stage:"Qualification", deals:218, amount:"$8.4M"},
{stage:"Proposal", deals:142, amount:"$6.1M"},
{stage:"Negotiation", deals:89, amount:"$4.2M"},
{stage:"Closed Won", deals:54, amount:"$2.8M"},
{stage:"Closed Lost", deals:35, amount:"$1.4M"}
]

const performers = [
{name:"Sarah Mitchell", revenue:"$892K"},
{name:"James Rodriguez", revenue:"$764K"},
{name:"Priya Sharma", revenue:"$698K"},
{name:"David Chen", revenue:"$612K"},
{name:"Emma Thompson", revenue:"$578K"}
]

export default function Page(){

return(

<div className="min-h-screen bg-background">

<Header/>

<div className="pt-[70px] px-6 space-y-6">

<h1 className="text-2xl font-bold">
Sales Analytics Hub
</h1>

{/* KPI STRIP */}

<div className="grid grid-cols-6 gap-4">

<KPI title="Total Revenue" value="$4.82M"/>
<KPI title="Conversion Rate" value="24.7%"/>
<KPI title="Avg Deal Size" value="$38,400"/>
<KPI title="Pipeline Velocity" value="$312K/day"/>
<KPI title="Win Rate" value="31.2%"/>
<KPI title="Open Deals" value="247"/>

</div>

{/* PIPELINE */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="font-semibold mb-4">
Sales Pipeline
</h2>

<div className="space-y-4">

{pipeline.map((p,i)=>(

<div key={i}>

<div className="flex justify-between text-sm mb-1">

<span>{p.stage}</span>

<span>{p.amount}</span>

</div>

<div className="h-3 bg-muted rounded-full">

<div
className="h-3 bg-blue-600 rounded-full"
style={{width:`${(p.deals/312)*100}%`}}
/>

</div>

</div>

))}

</div>

</div>

{/* TOP PERFORMERS */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="font-semibold mb-4">
Top Performers
</h2>

<div className="space-y-3">

{performers.map((p,i)=>(

<div
key={i}
className="flex justify-between border-b pb-2"
>

<span>{p.name}</span>

<span className="font-semibold">
{p.revenue}
</span>

</div>

))}

</div>

</div>

</div>

</div>

)

}

function KPI({title,value}:any){

return(

<div className="bg-card border border-border rounded-xl p-4">

<div className="text-sm text-muted-foreground">
{title}
</div>

<div className="text-lg font-bold">
{value}
</div>

</div>

)

}