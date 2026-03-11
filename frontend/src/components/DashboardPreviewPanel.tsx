"use client"

import ChartWidget from "./ChartWidget"

export default function DashboardPreviewPanel({charts=[]}:any){

if(charts.length===0){

return(

<div className="flex items-center justify-center h-full text-muted-foreground">

No Dashboard Yet

</div>

)

}

return(

<div className="p-6 space-y-6 overflow-y-auto">

{charts.map((chart:any)=>(

<div
key={chart.id}
className="bg-card border border-border rounded-xl shadow-card p-6"
>

<h3 className="text-lg font-semibold mb-4">

{chart.title}

</h3>

<ChartWidget key={chart.id} chart={chart}/>

</div>

))}

</div>

)

}