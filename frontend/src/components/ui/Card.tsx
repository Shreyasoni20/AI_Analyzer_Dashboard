"use client"

export default function Card({
title,
children
}:{
title?:string
children:any
}){

return(

<div className="bg-card text-card-foreground border border-border rounded-xl shadow-card p-6">

{title && (

<h3 className="text-lg font-semibold mb-4">
{title}
</h3>

)}

{children}

</div>

)

}
