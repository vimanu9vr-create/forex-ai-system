interface Props {
  size?: 'sm' | 'md' | 'lg'
  text?: string
}

export default function LoadingSpinner({ size = 'md', text }: Props) {
  const sizes = { sm: 'w-4 h-4', md: 'w-8 h-8', lg: 'w-12 h-12' }

  return (
    <div className="flex flex-col items-center justify-center gap-3 p-8">
      <div
        className={`${sizes[size]} border-2 border-zinc-700 border-t-emerald-400 rounded-full animate-spin`}
      />
      {text && <p className="text-zinc-500 text-sm font-mono">{text}</p>}
    </div>
  )
}
