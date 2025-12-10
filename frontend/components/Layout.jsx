import Sidebar from './Sidebar';
import Head from 'next/head';

export default function Layout({ children, title = 'Cortana AI' }) {
  const pageTitle = `${title} - Doxen Strategy Group`;
  
  return (
    <>
      <Head>
        <title>{pageTitle}</title>
        <meta name="description" content="AI Voice Automation System" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <div className="flex min-h-screen">
        <Sidebar />
        <main className="flex-1 ml-64 p-8">
          {children}
        </main>
      </div>
    </>
  );
}
