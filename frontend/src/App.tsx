import { Route, Switch } from 'react-router-dom'
import { ToastProvider } from './components/common/ToastProvider'
import { AppLayout } from './layouts/AppLayout'
import { ChatPage } from './pages/ChatPage'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { MemoriesPage } from './pages/MemoriesPage'
import { RelationshipPage } from './pages/RelationshipPage'
import { SettingsPage } from './pages/SettingsPage'
import { AppProvider } from './state/AppContext'
import { SettingsProvider } from './state/SettingsContext'

export default function App() {
  return (
    <ToastProvider>
      <SettingsProvider>
        <AppProvider>
          <AppLayout>
            <Switch>
              <Route exact path="/" component={HomePage} />
              <Route exact path="/chat/:conversationId" component={ChatPage} />
              <Route
                exact
                path="/relationship/:conversationId"
                component={RelationshipPage}
              />
              <Route
                exact
                path="/memories/:conversationId"
                component={MemoriesPage}
              />
              <Route exact path="/settings" component={SettingsPage} />
              <Route component={NotFoundPage} />
            </Switch>
          </AppLayout>
        </AppProvider>
      </SettingsProvider>
    </ToastProvider>
  )
}
