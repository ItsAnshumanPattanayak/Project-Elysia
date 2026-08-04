import { Route, Switch } from 'react-router-dom'
import { ToastProvider } from './components/common/ToastProvider'
import { AppLayout } from './layouts/AppLayout'
import { ChatPage } from './pages/ChatPage'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { AppProvider } from './state/AppContext'

export default function App() {
  return (
    <ToastProvider>
      <AppProvider>
        <AppLayout>
          <Switch>
            <Route exact path="/" component={HomePage} />
            <Route exact path="/chat/:conversationId" component={ChatPage} />
            <Route component={NotFoundPage} />
          </Switch>
        </AppLayout>
      </AppProvider>
    </ToastProvider>
  )
}
