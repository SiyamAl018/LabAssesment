// Initial frontend contracts; align these with Siyam and Khalid before integration.
export interface Farm { id: string; name: string; location?: string }
export interface Visit { id: string; farmId: string; visitedAt: string; problem: string; advice: string; followUp?: string; dueDate?: string }
export interface Reminder { id: string; farmId: string; farmName: string; promise: string; dueDate: string; completed: boolean }
