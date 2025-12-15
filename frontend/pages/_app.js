import '../styles/globals.css';
import { BusinessProvider } from '../contexts/BusinessContext';

export default function App({ Component, pageProps }) {
  return (
    <BusinessProvider>
      <Component {...pageProps} />
    </BusinessProvider>
  );
}
