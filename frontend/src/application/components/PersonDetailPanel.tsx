import React, { useEffect, useState } from 'react';
import { DetailedPersonData } from '../types';
import { getGenderIcon, getGenderColor, getGenderLabel } from '../utils/gender';

interface PersonDetailPanelProps {
  personId: string | null;
  onClose: () => void;
}

export const PersonDetailPanel: React.FC<PersonDetailPanelProps> = ({ personId, onClose }) => {
  const [person, setPerson] = useState<DetailedPersonData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!personId) {
      setPerson(null);
      return;
    }

    const fetchPersonDetails = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/people/${personId}/`);
        if (!response.ok) {
          throw new Error('Failed to fetch person details');
        }
        const data = await response.json();
        setPerson(data);
      } catch (err) {
        console.error('Error fetching person details:', err);
        setError(err instanceof Error ? err.message : 'Failed to load person details');
      } finally {
        setIsLoading(false);
      }
    };

    fetchPersonDetails();
  }, [personId]);

  if (!personId) {
    return null;
  }

  const getFullName = (nameObj?: { first_name: string; middle_name: string; last_name: string }) => {
    if (!nameObj) return 'Unknown';
    return `${nameObj.first_name} ${nameObj.middle_name} ${nameObj.last_name}`.trim();
  };

  return (
    <div
      style={{
        width: '400px',
        height: '100vh',
        backgroundColor: '#2a2a2a',
        color: '#fff',
        boxShadow: '-4px 0 12px rgba(0,0,0,0.3)',
        overflowY: 'auto',
        fontFamily: 'Roboto, sans-serif',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          padding: '20px',
        }}
      >
        {/* Header with close button */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
          }}
        >
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 'bold' }}>Person Details</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#fff',
              fontSize: '24px',
              cursor: 'pointer',
              padding: '0',
              width: '30px',
              height: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            title="Close panel"
          >
            ×
          </button>
        </div>

        {/* Loading state */}
        {isLoading && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
            Loading person details...
          </div>
        )}

        {/* Error state */}
        {error && (
          <div style={{
            padding: '20px',
            backgroundColor: '#3a2a2a',
            borderRadius: '8px',
            color: '#ff8888',
            marginBottom: '20px'
          }}>
            Error: {error}
          </div>
        )}

        {/* Content - only show when loaded and no error */}
        {!isLoading && !error && person && (
          <>
            {/* Person card */}
            <div
              style={{
                backgroundColor: getGenderColor(person.gender),
                borderRadius: '8px',
                padding: '20px',
                marginBottom: '20px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  marginBottom: '10px',
                }}
              >
                <div
                  style={{
                    width: '80px',
                    height: '80px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(255,255,255,0.2)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '15px',
                    fontSize: '36px',
                  }}
                >
                  {getGenderIcon(person.gender)}
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '22px', fontWeight: 'bold' }}>
                    {getFullName(person.name)}
                  </h3>
                  <p style={{ margin: '5px 0 0 0', fontSize: '14px', opacity: 0.9 }}>
                    {getGenderLabel(person.gender)}
                  </p>
                </div>
              </div>
            </div>

            {/* Names */}
            {person.names && person.names.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                  Names
                </h3>
                <div style={{ paddingLeft: '10px' }}>
                  {person.names.map((name, index) => (
                    <div key={index} style={{ marginBottom: '8px' }}>
                      <span style={{ fontSize: '14px' }}>{getFullName(name)}</span>
                      {name.name_type && (
                        <span style={{ color: '#999', fontSize: '12px', marginLeft: '8px' }}>
                          ({name.name_type})
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Life Events */}
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                Life Events
              </h3>
              <div style={{ paddingLeft: '10px' }}>
                {person.birth && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#aaa' }}>Birth</div>
                    {person.birth.date && (
                      <div style={{ fontSize: '14px', marginLeft: '10px' }}>Date: {person.birth.date}</div>
                    )}
                    {person.birth.location && (
                      <div style={{ fontSize: '14px', marginLeft: '10px' }}>Location: {person.birth.location}</div>
                    )}
                    {person.birth.comment && (
                      <div style={{ fontSize: '14px', marginLeft: '10px', fontStyle: 'italic' }}>
                        {person.birth.comment}
                      </div>
                    )}
                  </div>
                )}

                {person.death && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#aaa' }}>Death</div>
                    {person.death.date && (
                      <div style={{ fontSize: '14px', marginLeft: '10px' }}>Date: {person.death.date}</div>
                    )}
                    {person.death.location && (
                      <div style={{ fontSize: '14px', marginLeft: '10px' }}>Location: {person.death.location}</div>
                    )}
                    {person.death.cause && (
                      <div style={{ fontSize: '14px', marginLeft: '10px' }}>Cause: {person.death.cause}</div>
                    )}
                    {person.death.comment && (
                      <div style={{ fontSize: '14px', marginLeft: '10px', fontStyle: 'italic' }}>
                        {person.death.comment}
                      </div>
                    )}
                  </div>
                )}

                {!person.birth && !person.death && (
                  <div style={{ color: '#999', fontSize: '14px' }}>No life event data available</div>
                )}
              </div>
            </div>

            {/* Marriages */}
            {person.marriages && person.marriages.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                  Marriages ({person.marriages.length})
                </h3>
                <div style={{ paddingLeft: '10px' }}>
                  {person.marriages.map((marriage, index) => (
                    <div key={marriage.id} style={{ marginBottom: '12px' }}>
                      <div style={{ fontSize: '14px' }}>
                        • {getFullName(marriage.other_person.name)} ({getGenderLabel(marriage.other_person.gender)})
                        {marriage.ended && <span style={{ color: '#ff8888', marginLeft: '8px' }}>(Ended)</span>}
                      </div>
                      {marriage.date && (
                        <div style={{ fontSize: '12px', color: '#999', marginLeft: '10px' }}>
                          Date: {marriage.date}
                        </div>
                      )}
                      {marriage.location && (
                        <div style={{ fontSize: '12px', color: '#999', marginLeft: '10px' }}>
                          Location: {marriage.location}
                        </div>
                      )}
                      {marriage.comment && (
                        <div style={{ fontSize: '12px', color: '#999', marginLeft: '10px', fontStyle: 'italic' }}>
                          {marriage.comment}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Immigration & Citizenship */}
            {((person.immigrations && person.immigrations.length > 0) ||
              (person.citizenships && person.citizenships.length > 0)) && (
              <div style={{ marginBottom: '20px' }}>
                <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                  Immigration & Citizenship
                </h3>
                <div style={{ paddingLeft: '10px' }}>
                  {person.immigrations?.map((immigration, index) => (
                    <div key={immigration.id} style={{ marginBottom: '12px' }}>
                      <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#aaa' }}>Immigration</div>
                      {immigration.date && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>Date: {immigration.date}</div>
                      )}
                      {immigration.from_country && immigration.to_country && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>
                          From {immigration.from_country} to {immigration.to_country}
                        </div>
                      )}
                      {immigration.location && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>Location: {immigration.location}</div>
                      )}
                    </div>
                  ))}
                  {person.citizenships?.map((citizenship, index) => (
                    <div key={citizenship.id} style={{ marginBottom: '12px' }}>
                      <div style={{ fontSize: '14px', fontWeight: 'bold', color: '#aaa' }}>Citizenship</div>
                      {citizenship.date && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>Date: {citizenship.date}</div>
                      )}
                      {citizenship.country && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>Country: {citizenship.country}</div>
                      )}
                      {citizenship.location && (
                        <div style={{ fontSize: '14px', marginLeft: '10px' }}>Location: {citizenship.location}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Relationships */}
            <div style={{ marginBottom: '20px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                Family Relationships
              </h3>
              <div style={{ paddingLeft: '10px' }}>
                {/* Parents */}
                {person.parents && person.parents.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ color: '#999', fontSize: '14px', marginBottom: '5px' }}>Parents:</div>
                    {person.parents.map((parent) => (
                      <div key={parent.id} style={{ fontSize: '14px', marginLeft: '10px' }}>
                        • {getFullName(parent.name)} ({getGenderLabel(parent.gender)})
                      </div>
                    ))}
                  </div>
                )}

                {/* Children */}
                {person.children && person.children.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ color: '#999', fontSize: '14px', marginBottom: '5px' }}>
                      Children ({person.children.length}):
                    </div>
                    {person.children.map((child) => (
                      <div key={child.id} style={{ fontSize: '14px', marginLeft: '10px' }}>
                        • {getFullName(child.name)} ({getGenderLabel(child.gender)})
                      </div>
                    ))}
                  </div>
                )}

                {/* Siblings */}
                {person.siblings && person.siblings.length > 0 && (
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ color: '#999', fontSize: '14px', marginBottom: '5px' }}>
                      Siblings ({person.siblings.length}):
                    </div>
                    {person.siblings.map((sibling) => (
                      <div key={sibling.id} style={{ fontSize: '14px', marginLeft: '10px' }}>
                        • {getFullName(sibling.name)} ({getGenderLabel(sibling.gender)})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div style={{ marginTop: '30px', paddingTop: '20px', borderTop: '1px solid #444' }}>
              <h3 style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '10px', color: '#f0f0f0' }}>
                Quick Actions
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <a
                  href={`/admin/person/person/add/?children=${person.id}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: '#789fac',
                    textDecoration: 'none',
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                >
                  + Add parent
                </a>
                <a
                  href={`/admin/person/person/add/?${person.parents && person.parents.length > 0 ? `parents=${person.parents.map(p => p.id).join(',')}` : ''}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: '#789fac',
                    textDecoration: 'none',
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                >
                  + Add sibling
                </a>
                <a
                  href={`/admin/person/person/add/?parents=${person.id}`}
                  target="_blank"
                  rel="noreferrer"
                  style={{
                    color: '#789fac',
                    textDecoration: 'none',
                    fontSize: '14px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                  }}
                >
                  + Add child
                </a>
              </div>
            </div>

            {/* Edit link */}
            <div style={{ marginTop: '20px', paddingTop: '20px', borderTop: '1px solid #444' }}>
              <a
                href={`/admin/person/person/${person.id}/change/`}
                target="_blank"
                rel="noreferrer"
                style={{
                  color: '#789fac',
                  textDecoration: 'none',
                  fontSize: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '5px',
                }}
              >
                ✎ Edit person details
              </a>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
