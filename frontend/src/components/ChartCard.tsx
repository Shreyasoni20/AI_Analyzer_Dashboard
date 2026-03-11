"use client"

export default function ChartCard({

title,
children

}:{title:string,children:any}){

return(

<div className="bg-white border border-border rounded-xl shadow-sm p-6">

<h2 className="text-lg font-semibold mb-4">
{title}
</h2>

{children}

</div>

)

}