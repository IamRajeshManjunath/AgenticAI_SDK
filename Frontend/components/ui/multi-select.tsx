'use client'

import * as React from 'react'
import { X, Check, ChevronsUpDown, Plus } from 'lucide-react'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'

interface MultiSelectOption {
  label: string
  value: string
  group?: string
}

interface MultiSelectProps {
  options: MultiSelectOption[]
  selected: string[]
  onChange: (selected: string[]) => void
  placeholder?: string
  creatable?: boolean
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = 'Select...',
  creatable = false,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')

  const selectedSet = React.useMemo(() => new Set(selected), [selected])

  const groupedOptions = React.useMemo(() => {
    const groups: Record<string, { label: string; value: string }[]> = {}
    for (const opt of options) {
      const g = opt.group || 'Other'
      if (!groups[g]) groups[g] = []
      groups[g].push({ label: opt.label, value: opt.value })
    }
    return groups
  }, [options])

  const showCustom = creatable && search && !options.some((o) => o.value === search)

  const toggleValue = (value: string) => {
    const next = new Set(selected)
    if (next.has(value)) {
      next.delete(value)
    } else {
      next.add(value)
    }
    onChange(Array.from(next))
  }

  const removeValue = (value: string) => {
    onChange(selected.filter((v) => v !== value))
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full h-auto min-h-9 justify-between"
        >
          <div className="flex flex-wrap gap-1 flex-1">
            {selected.length === 0 && (
              <span className="text-muted-foreground text-sm">{placeholder}</span>
            )}
            {selected.map((value) => {
              const opt = options.find((o) => o.value === value)
              return (
                <Badge
                  key={value}
                  variant="secondary"
                  className="text-xs font-mono gap-1"
                >
                  {opt?.label || value}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      removeValue(value)
                    }}
                    className="hover:text-destructive"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              )
            })}
          </div>
          <ChevronsUpDown className="w-4 h-4 shrink-0 opacity-50 ml-1" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[var(--radix-popover-trigger-width)] p-0">
        <Command>
          <CommandInput
            placeholder={`Search ${placeholder.toLowerCase()}...`}
            value={search}
            onValueChange={setSearch}
          />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            {showCustom && (
              <CommandGroup>
                <CommandItem
                  value={search}
                  onSelect={() => {
                    toggleValue(search)
                    setSearch('')
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add &quot;{search}&quot;
                </CommandItem>
              </CommandGroup>
            )}
            {Object.entries(groupedOptions).map(([group, items], gi) => (
              <React.Fragment key={group}>
                {gi > 0 && <CommandSeparator />}
                <CommandGroup heading={group}>
                  {items.map((item) => (
                    <CommandItem
                      key={item.value}
                      value={item.value}
                      onSelect={() => {
                        toggleValue(item.value)
                        setSearch('')
                      }}
                    >
                      <Check
                        className={cn(
                          'w-4 h-4 mr-2',
                          selectedSet.has(item.value) ? 'opacity-100' : 'opacity-0'
                        )}
                      />
                      <span className="font-mono text-xs">{item.label}</span>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </React.Fragment>
            ))}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
