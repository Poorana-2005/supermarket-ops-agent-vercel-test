# 4–5 Minute Demo Script

Use a fresh Telegram chat.

1. **Receive stock**
   Say: `received 10 Aashirvaad Atta 5kg`
   Show the tool-confirmed new stock.

2. **Multi-item bill**
   Say: `make a bill: 2 atta and 3 tata salt`
   Agent creates a draft and shows GST/total.

3. **Edit**
   Say: `change salt to 2`
   Show updated draft.

4. **Oversell guard**
   Say: `add 999 atta`
   Show that the tool refuses because stock is insufficient.

5. **Payment + finalization**
   Say: `UPI reference UPI-DEMO-001, finalise`
   Show bill number and total.

6. **PDF**
   Say: `create PDF invoice for that bill`
   Telegram returns the real PDF.

7. **Khata**
   Say: `put 500 on Ramesh credit`
   Then: `Ramesh paid 300`
   Then: `Ramesh balance`
   Show ₹200.

8. **Analysis deck**
   Say: `create today's analysis deck`
   Telegram returns PPTX.

9. **Preference**
   Say: `remember default payment is UPI and default product is atta`
   Then `/new`.
   Ask: `what are my defaults?`
   Show that preferences remain.

Keep the explanation focused on agent control loop, tool-layer guardrails, transactional stock, GST, durable memory and real artifacts.
