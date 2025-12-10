import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import GlassCard from '../components/GlassCard';
import GlassButton from '../components/GlassButton';
import GlowInput from '../components/GlowInput';

export default function Knowledgebase() {
  const [documents, setDocuments] = useState([]);
  const [showEditor, setShowEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState(null);
  const [formData, setFormData] = useState({ title: '', content: '', category: '' });
  const businessId = 1;

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`/api/knowledgebase/${businessId}`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (e) {
      console.log('Error fetching documents');
    }
  };

  const handleSave = async () => {
    try {
      const url = editingDoc 
        ? `/api/knowledgebase/${businessId}/${editingDoc.id}`
        : `/api/knowledgebase/${businessId}`;
      
      const res = await fetch(url, {
        method: editingDoc ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (res.ok) {
        fetchDocuments();
        closeEditor();
      }
    } catch (e) {
      console.error('Error saving document');
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      const res = await fetch(`/api/knowledgebase/${businessId}/${docId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        fetchDocuments();
      }
    } catch (e) {
      console.error('Error deleting document');
    }
  };

  const openEditor = (doc = null) => {
    if (doc) {
      setEditingDoc(doc);
      setFormData({ title: doc.title, content: doc.content, category: doc.category || '' });
    } else {
      setEditingDoc(null);
      setFormData({ title: '', content: '', category: '' });
    }
    setShowEditor(true);
  };

  const closeEditor = () => {
    setShowEditor(false);
    setEditingDoc(null);
    setFormData({ title: '', content: '', category: '' });
  };

  return (
    <Layout title="Knowledgebase">
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold mb-2">Knowledgebase</h1>
          <p className="text-white/60">Manage AI knowledge and responses</p>
        </div>
        <GlassButton variant="primary" onClick={() => openEditor()}>
          + Add Document
        </GlassButton>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {documents.length === 0 ? (
          <div className="col-span-full">
            <GlassCard className="text-center py-12">
              <p className="text-4xl mb-4">📚</p>
              <p className="text-white/60">No documents yet. Add your first knowledge base document.</p>
            </GlassCard>
          </div>
        ) : (
          documents.map((doc) => (
            <GlassCard key={doc.id}>
              <div className="flex justify-between items-start mb-3">
                <h3 className="font-semibold text-lg">{doc.title}</h3>
                {doc.category && (
                  <span className="text-xs px-2 py-1 bg-neon-purple/20 text-neon-purple rounded">
                    {doc.category}
                  </span>
                )}
              </div>
              <p className="text-white/60 text-sm mb-4 line-clamp-3">{doc.content}</p>
              <div className="flex gap-2">
                <button 
                  onClick={() => openEditor(doc)}
                  className="text-sm text-neon-blue hover:underline"
                >
                  Edit
                </button>
                <button 
                  onClick={() => handleDelete(doc.id)}
                  className="text-sm text-red-400 hover:underline"
                >
                  Delete
                </button>
              </div>
              <p className="text-xs text-white/40 mt-3">
                Updated: {doc.updated_at ? new Date(doc.updated_at).toLocaleDateString() : 'N/A'}
              </p>
            </GlassCard>
          ))
        )}
      </div>

      {showEditor && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="glass-card p-6 max-w-lg w-full mx-4">
            <h2 className="text-xl font-bold mb-4">
              {editingDoc ? 'Edit Document' : 'New Document'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-white/60 mb-2">Title</label>
                <GlowInput
                  value={formData.title}
                  onChange={(e) => setFormData({...formData, title: e.target.value})}
                  placeholder="Document title"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Category</label>
                <GlowInput
                  value={formData.category}
                  onChange={(e) => setFormData({...formData, category: e.target.value})}
                  placeholder="e.g., Services, Pricing, FAQ"
                />
              </div>
              <div>
                <label className="block text-sm text-white/60 mb-2">Content</label>
                <textarea
                  value={formData.content}
                  onChange={(e) => setFormData({...formData, content: e.target.value})}
                  placeholder="Document content that Cortana will use to answer questions..."
                  className="glow-input min-h-[200px] resize-none"
                />
              </div>
              <div className="flex gap-3 justify-end">
                <GlassButton onClick={closeEditor}>Cancel</GlassButton>
                <GlassButton variant="primary" onClick={handleSave}>Save</GlassButton>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
