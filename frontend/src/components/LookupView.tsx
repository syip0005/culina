import { useState, useEffect, useRef } from 'react'
import { lookup, createNutritionEntry, addMealItem, createMeal } from '../api.ts'
import { NutritionSummary } from './NutritionSummary.tsx'
import { isSearchNutritionInfo } from '../types.ts'
import type {
  Meal,
  MealType,
  LookupResponse,
  SearchNutritionInfo,
  SearchNutritionNotFound,
} from '../types.ts'

interface Props {
  initialQuery: string
  mealType: MealType
  mealId: string | null
  onMealCreated: (meal: Meal) => void
  onItemAdded: () => void
  onBack: () => void
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  response?: LookupResponse
}

export function LookupView({ initialQuery, mealType, mealId, onMealCreated, onItemAdded, onBack }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [currentMealId, setCurrentMealId] = useState<string | null>(mealId)
  const [addedItems, setAddedItems] = useState<Set<string>>(new Set())
  const [addingQuantity, setAddingQuantity] = useState<{ item: SearchNutritionInfo; quantity: string } | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

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
    if (initialQuery.trim()) {
      sendMessage(initialQuery)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const ensureMeal = async (): Promise<string> => {
    if (currentMealId) return currentMealId
    const meal = await createMeal({
      meal_type: mealType,
      eaten_at: new Date().toISOString(),
    })
    setCurrentMealId(meal.id)
    onMealCreated(meal)
    return meal.id
  }

  const handleAddItem = (item: SearchNutritionInfo) => {
    setAddingQuantity({ item, quantity: '1' })
  }

  const confirmAdd = async () => {
    if (!addingQuantity) return

    const { item, quantity } = addingQuantity
    const qty = parseFloat(quantity) || 1

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
      alert(e instanceof Error ? e.message : 'Failed to add item')
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
                              {info.serving_amount}{info.serving_unit}
                              {info.serving_description && ` (${info.serving_description})`}
                            </div>
                            <NutritionSummary
                              energyKj={info.energy_kj}
                              proteinG={info.protein_g}
                              fatG={info.fat_g}
                              carbsG={info.carbs_g}
                            />
                            {isAdded ? (
                              <div className="text-muted text-sm mt-1">Added</div>
                            ) : isAddingThis ? (
                              <div className="quantity-inline">
                                <input
                                  type="number"
                                  value={addingQuantity.quantity}
                                  onChange={(e) => setAddingQuantity({ ...addingQuantity, quantity: e.target.value })}
                                  step="0.5"
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

            {loading && <div className="lookup-message">Thinking...</div>}
            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="overlay-footer">
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
    </div>
  )
}
