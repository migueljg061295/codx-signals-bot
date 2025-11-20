# Bot de Señales TradingView -> Telegram

## Cómo usar
1. Configura las variables de entorno en Render (BOT_TOKEN, CHANNEL_FREE, CHANNEL_VIP)
2. Crea alertas en TradingView apuntando a los endpoints:
   - Free: https://TU_APP.onrender.com/webhook/free
   - VIP: https://TU_APP.onrender.com/webhook/vip
   - Cierre Free: https://TU_APP.onrender.com/webhook/free/close
   - Cierre VIP: https://TU_APP.onrender.com/webhook/vip/close
3. Formato JSON de las alertas:
   {
     "symbol": "BTCUSDT",
     "action": "BUY",
     "entry_price": 27950,
     "leverage": 10,
     "win_rate": 80
   }
4. Para alertas de cierre añade `"outcome": "TP"` o `"SL"`
