"use client"

import Header from "@/components/common/Header"
import {
ResponsiveContainer,
LineChart,
Line,
XAxis,
YAxis,
Tooltip
} from "recharts"

const revenueData = [
{month:"Jan",revenue:32000},
{month:"Feb",revenue:38000},
{month:"Mar",revenue:45000},
{month:"Apr",revenue:52000},
{month:"May",revenue:56000},
{month:"Jun",revenue:62000}
]

const departments = [
{ name:"Sales", score:94, status:"good" },
{ name:"Marketing", score:88, status:"good" },
{ name:"Operations", score:76, status:"warn" },
{ name:"Finance", score:91, status:"good" },
{ name:"Human Resources", score:79, status:"warn" },
{ name:"Product", score:68, status:"bad" }
]

export default function Page(){

return(

<div className="min-h-screen bg-background">

<Header/>

<div className="pt-[70px] px-6 space-y-6">

<h1 className="text-2xl font-bold">
Executive Overview
</h1>

{/* KPI CARDS */}

<div className="grid grid-cols-4 gap-4">

<KPI title="Total Revenue" value="$48.7M" change="+12.4%" />
<KPI title="Growth Rate" value="12.4%" change="+2.1%" />
<KPI title="Customer Acquisition" value="3,842" change="-1.2%" />
<KPI title="Operational Efficiency" value="87.3%" change="+1.8%" />

</div>

{/* REVENUE TREND */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="text-lg font-semibold mb-4">
Revenue Trends & Goal Tracking
</h2>

<ResponsiveContainer width="100%" height={300}>

<LineChart data={revenueData}>

<XAxis dataKey="month"/>

<YAxis/>

<Tooltip/>

<Line
type="monotone"
dataKey="revenue"
stroke="#2563EB"
strokeWidth={3}
/>

</LineChart>

</ResponsiveContainer>

</div>

{/* DEPARTMENT SCORECARDS */}

<div className="bg-card border border-border rounded-xl p-6">

<h2 className="text-lg font-semibold mb-4">
Department Performance Scorecards
</h2>

<div className="grid grid-cols-3 gap-4">

{departments.map((d,i)=>(
<div
key={i}
className="border rounded-lg p-4 bg-muted"
>

<div className="font-semibold">
{d.name}
</div>

<div className="text-2xl font-bold mt-2">
{d.score}
</div>

</div>
))}

</div>

</div>

</div>

</div>

)

}

function KPI({title,value,change}:any){

return(

<div className="bg-card border border-border rounded-xl p-4">

<div className="text-sm text-muted-foreground">
{title}
</div>

<div className="text-xl font-bold">
{value}
</div>

<div className="text-green-600 text-sm">
{change}
</div>

</div>

)

}