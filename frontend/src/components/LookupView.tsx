import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../auth.tsx'
import { lookup, createNutritionEntry, addMealItem, createMeal } from '../api.ts'
import { dateMidpointISO } from '../utils/date.ts'
import { isScalableUnit, servingLabel } from '../utils/serving.ts'
import { PencilIcon } from './Icons.tsx'
import { NutritionSummary } from './NutritionSummary.tsx'
import { EditEntryPanel } from './EditEntryPanel.tsx'
import { isSearchNutritionInfo } from '../types.ts'
import type {
  Meal,
  MealType,
  LookupResponse,
  SearchNutritionInfo,
  SearchNutritionNotFound,
  EnergyUnit,
} from '../types.ts'

const THINKING_PHRASES = [
  'Manducating bulgogi',
  'Lucubrating custards',
  'Excogitating charcoals',
  'Peragrating potatoes',
  'Oblectating mussels',
  'Ruminating kimchi',
  'Mullering menus',
  'Disputating dumplings',
  'Savouring suppositions',
  'Cogitating cookfires',
  'Speculating suppers',
  'Contemplating tubers',
  'Deliberating delicacies',
  'Meditating marinades',
  'Reckoning roasts',
  'Pondering provender',
  'Excursating entrées',
  'Palating possibilities',
  'Gustating gently',
  'Ideating indulgences',
  'Deglazing',
  'Infusing',
  'Reducing',
  'Rendering',
  'Braising',
  'Caramelising',
  'Charring',
  'Curating flavours',
  'Profiling taste',
  'Balancing notes',
  'Composing plates',
  'Elevating choices',
  'Foraging ideas',
  'Fermenting thoughts',
  'Gustating options',
  'Relishing possibilities',
  'Indulging curiosity',
  'Titillating tastebuds',
  'Plating inspiration',
]

function useThinkingPhrase(active: boolean) {
  const [index, setIndex] = useState(() => Math.floor(Math.random() * THINKING_PHRASES.length))

  useEffect(() => {
    if (!active) return
    setIndex(Math.floor(Math.random() * THINKING_PHRASES.length))
    const id = setInterval(() => {
      setIndex((prev) => {
        let next: number
        do { next = Math.floor(Math.random() * THINKING_PHRASES.length) } while (next === prev)
        return next
      })
    }, 2500)
    return () => clearInterval(id)
  }, [active])

  return THINKING_PHRASES[index]
}

function ThinkingIndicator() {
  const [dots, setDots] = useState('')

  useEffect(() => {
    const id = setInterval(() => {
      setDots((prev) => prev.length >= 3 ? '' : prev + '.')
    }, 700)
    return () => clearInterval(id)
  }, [])

  return <span>{dots}</span>
}

interface Props {
  initialQuery: string
  mealType: MealType
  mealId: string | null
  targetDate: string
  timezone: string
  onMealCreated: (meal: Meal) => void
  onItemAdded: () => void
  onBack: () => void
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  response?: LookupResponse
}

export function LookupView({ initialQuery, mealType, mealId, targetDate, timezone, onMealCreated, onItemAdded, onBack }: Props) {
  const { user } = useAuth()
  const eUnit = (user?.settings?.preferred_energy_unit ?? 'kj') as EnergyUnit
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentMealId, setCurrentMealId] = useState<string | null>(mealId)
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set())
  const [addError, setAddError] = useState<string | null>(null)
  const [addingQuantity, setAddingQuantity] = useState<{ item: SearchNutritionInfo; quantity: string } | null>(null)
  const [editingItem, setEditingItem] = useState<{ msgIndex: number; itemIndex: number; item: SearchNutritionInfo } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sentInitial = useRef(false)
  const thinkingPhrase = useThinkingPhrase(loading)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(scrollToBottom, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setLoading(true)
    setInput('')

    try {
      const res = await lookup({
        text,
        conversation_id: conversationId ?? undefined,
      })
      setConversationId(res.conversation_id)

      const assistantContent = res.kind === 'follow_up'
        ? res.follow_up_question
        : `Found ${res.result.items.length} item(s)`

      setMessages((prev) => [...prev, { role: 'assistant', content: assistantContent, response: res }])
    } catch (e) {
      setMessages((prev) => [...prev, {
        role: 'assistant',
        content: `Error: ${e instanceof Error ? e.message : 'Unknown error'}`,
      }])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialQuery.trim() && !sentInitial.current) {
      sentInitial.current = true
      sendMessage(initialQuery)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const ensureMeal = async (): Promise<string> => {
    if (currentMealId) return currentMealId
    const meal = await createMeal({
      meal_type: mealType,
      eaten_at: dateMidpointISO(targetDate, timezone),
    })
    setCurrentMealId(meal.id)
    onMealCreated(meal)
    return meal.id
  }

  const handleAddItem = (item: SearchNutritionInfo) => {
    const defaultValue = isScalableUnit(item.serving_unit)
      ? String(item.serving_amount)
      : '1'
    setAddingQuantity({ item, quantity: defaultValue })
  }

  const confirmAdd = async () => {
    if (!addingQuantity) return

    const { item, quantity } = addingQuantity
    const num = parseFloat(quantity) || 1
    // For g/ml: quantity = userAmount / baseServingAmount
    // For piece/serve: quantity = userValue directly
    const qty = isScalableUnit(item.serving_unit)
      ? num / item.serving_amount
      : num

    setAddError(null)
    try {
      const entry = await createNutritionEntry({
        food_item: item.food_item,
        brand: item.brand || '',
        source_url: item.source_url || '',
        serving_amount: item.serving_amount,
        serving_unit: item.serving_unit,
        serving_description: item.serving_description,
        energy_kj: item.energy_kj,
        protein_g: item.protein_g,
        fat_g: item.fat_g,
        carbs_g: item.carbs_g,
        source: item.source,
        notes: item.notes,
      })

      const mId = await ensureMeal()
      await addMealItem(mId, { nutrition_entry_id: entry.id, quantity: qty })

      const key = `${item.food_item}-${item.brand}-${item.energy_kj}`
      setAddedItems((prev) => new Set(prev).add(key))
      setAddingQuantity(null)
      onItemAdded()
    } catch (e) {
      setAddError(e instanceof Error ? e.message : 'Failed to add item')
    }
  }

  const itemKey = (item: SearchNutritionInfo) =>
    `${item.food_item}-${item.brand}-${item.energy_kj}`

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    sendMessage(input)
  }

  return (
    <div className="overlay second">
      <div className="overlay-inner">
        <div className="overlay-header">
          <h2>Find New Items</h2>
          <button className="secondary" onClick={onBack} style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}>
            Back
          </button>
        </div>

        <div className="overlay-body">
          <div className="lookup-messages">
            {messages.map((msg, i) => (
              <div key={i}>
                <div className={`lookup-message ${msg.role}`}>
                  {msg.content}
                </div>

                {msg.response?.kind === 'follow_up' && (
                  <div className="lookup-buttons">
                    {msg.response.follow_up_buttons.map((btn) => (
                      <button
                        key={btn}
                        onClick={() => sendMessage(btn)}
                        disabled={loading}
                      >
                        {btn}
                      </button>
                    ))}
                  </div>
                )}

                {msg.response?.kind === 'result' && (
                  <div style={{ marginTop: '0.5rem' }}>
                    {msg.response.result.items.map((resultItem, j) => {
                      if (isSearchNutritionInfo(resultItem)) {
                        const info = resultItem as SearchNutritionInfo
                        const key = itemKey(info)
                        const isAdded = addedItems.has(key)
                        const isAddingThis = addingQuantity?.item === info

                        return (
                          <div key={j} className="lookup-result-item">
                            <div className="name">{info.food_item}</div>
                            {info.brand && <div className="meta">{info.brand}</div>}
                            <div className="meta">
                              {servingLabel(info.serving_amount, info.serving_unit, info.serving_description)}
                            </div>
                            <NutritionSummary
                              energyKj={info.energy_kj}
                              proteinG={info.protein_g}
                              fatG={info.fat_g}
                              carbsG={info.carbs_g}
                              energyUnit={eUnit}
                            />
                            <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.4rem', alignItems: 'center' }}>
                              <button
                                className="btn-info"
                                onClick={() => setEditingItem({ msgIndex: i, itemIndex: j, item: info })}
                                title="Edit item"
                              >
                                <PencilIcon size={14} />
                              </button>
                            </div>
                            {isAdded ? (
                              <div className="text-muted text-sm mt-1">Added</div>
                            ) : isAddingThis ? (
                              <div className="quantity-inline">
                                <label style={{ fontSize: '0.7rem', marginRight: '0.3rem' }}>
                                  {isScalableUnit(info.serving_unit) ? info.serving_unit : (info.serving_description || `${info.serving_amount} ${info.serving_unit}`)}:
                                </label>
                                <input
                                  type="number"
                                  value={addingQuantity.quantity}
                                  onChange={(e) => setAddingQuantity({ ...addingQuantity, quantity: e.target.value })}
                                  step={isScalableUnit(info.serving_unit) ? '1' : '0.5'}
                                  min="0.1"
                                />
                                <button onClick={confirmAdd} style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}>
                                  Confirm
                                </button>
                                <button
                                  className="secondary"
                                  onClick={() => setAddingQuantity(null)}
                                  style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                                >
                                  Cancel
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={() => handleAddItem(info)}
                                style={{ marginTop: '0.4rem', fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                              >
                                Add
                              </button>
                            )}
                          </div>
                        )
                      } else {
                        const notFound = resultItem as SearchNutritionNotFound
                        return (
                          <div key={j} className="lookup-not-found">
                            <strong>{notFound.food_item}</strong>: {notFound.reason}
                            {notFound.suggestions.length > 0 && (
                              <div className="mt-1">
                                Try: {notFound.suggestions.join(', ')}
                              </div>
                            )}
                          </div>
                        )
                      }
                    })}
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="lookup-message thinking">
                {thinkingPhrase}<ThinkingIndicator />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="overlay-footer">
          {addError && <div className="delete-error text-xs" style={{ marginBottom: '0.5rem' }}>{addError}</div>}
          <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a food..."
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button type="submit" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>
      {editingItem && (
        <EditEntryPanel
          item={editingItem.item}
          className="overlay third"
          energyUnit={eUnit}
          onSave={(updated) => {
            setMessages((prev) => prev.map((msg, mi) => {
              if (mi !== editingItem.msgIndex || msg.response?.kind !== 'result') return msg
              const newItems = [...msg.response.result.items]
              newItems[editingItem.itemIndex] = updated
              return {
                ...msg,
                response: { ...msg.response, result: { ...msg.response.result, items: newItems } }
              }
            }))
            setEditingItem(null)
          }}
          onClose={() => setEditingItem(null)}
        />
      )}
    </div>
  )
}
